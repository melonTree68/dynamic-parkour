import math

import torch
from isaacgym import gymapi, gymtorch

from legged_gym.utils.dynamic_terrain_suites import (
    DYNAMIC_TERRAIN_SUITES,
    get_suite_layouts,
    layout_actor_count,
    max_suite_actor_count,
    suite_names,
)


class DynamicObstacleManager:
    """Create and update optional dynamic obstacle actors.

    Heightfields/heightfield and triangle meshes stay static. Dynamic terrain is layered on
    top as Isaac Gym box actors whose root states are updated through the
    simulator root-state tensor.
    """

    SUPPORTED_TYPES = (
        "moving_hurdle",
        "shifting_gap",
        "changing_step_height",
        "time_varying_ramp",
    )
    INACTIVE_TYPE = "inactive"

    def __init__(self, gym, sim, device, cfg, num_envs):
        self.gym = gym
        self.sim = sim
        self.device = device
        self.cfg = cfg
        self.num_envs = num_envs
        self.enabled = bool(getattr(cfg, "enable", False))
        self.use_suites = bool(getattr(cfg, "use_suites", False))
        self.root_states = None

        if not self.enabled:
            return

        self._validate_cfg()
        self.all_env_ids = torch.arange(num_envs, dtype=torch.long, device=device)
        self.identity_quat = torch.tensor(
            [0.0, 0.0, 0.0, 1.0], dtype=torch.float, device=device
        )

        self.suite_layouts = (
            get_suite_layouts(self.cfg.suite) if self.use_suites else None
        )
        self.num_obstacles_per_env = self._num_obstacles_for_mode()
        self.actor_indices = torch.full(
            (num_envs, self.num_obstacles_per_env),
            -1,
            dtype=torch.long,
            device=device,
        )
        self.base_positions = torch.zeros(
            num_envs, self.num_obstacles_per_env, 3, dtype=torch.float, device=device
        )
        self.current_positions = torch.zeros_like(self.base_positions)
        self.current_velocities = torch.zeros_like(self.base_positions)
        self.current_orientations = torch.zeros(
            num_envs, self.num_obstacles_per_env, 4, dtype=torch.float, device=device
        )
        self.current_orientations[:, :, 3] = 1.0
        self.current_angular_velocities = torch.zeros_like(self.base_positions)

        self.amplitudes = torch.zeros(
            num_envs, self.num_obstacles_per_env, dtype=torch.float, device=device
        )
        self.frequencies = torch.zeros_like(self.amplitudes)
        self.phases = torch.zeros_like(self.amplitudes)
        self.reset_times = torch.zeros_like(self.amplitudes)
        self.current_offsets = torch.zeros_like(self.amplitudes)
        self.motion_multipliers = torch.ones_like(self.amplitudes)
        self.current_step_heights = torch.zeros_like(self.amplitudes)
        self.current_ramp_angles = torch.zeros_like(self.amplitudes)

        self.axis_ids = torch.zeros(
            num_envs, self.num_obstacles_per_env, dtype=torch.long, device=device
        )
        self.base_ramp_pitches = torch.zeros_like(self.amplitudes)
        self.step_heights = torch.zeros_like(self.amplitudes)
        self.active_mask = torch.zeros(
            num_envs, self.num_obstacles_per_env, dtype=torch.bool, device=device
        )
        self.motion_group_ids = torch.full(
            (num_envs, self.num_obstacles_per_env),
            -1,
            dtype=torch.long,
            device=device,
        )
        self.layout_ids = torch.full((num_envs,), -1, dtype=torch.long, device=device)
        self.actor_type_names = [
            [self.INACTIVE_TYPE for _ in range(self.num_obstacles_per_env)]
            for _ in range(num_envs)
        ]
        self.actor_slots_by_env = [[] for _ in range(num_envs)]
        self.assets = {}

    def create_assets(self):
        if not self.enabled:
            return

        asset_options = gymapi.AssetOptions()
        asset_options.density = self._asset_density()
        asset_options.disable_gravity = True
        asset_options.fix_base_link = bool(self.cfg.make_kinematic)
        asset_options.thickness = 0.01

        possible_layouts = self._possible_layouts()
        for layout in possible_layouts:
            for slot in self._expand_layout(layout):
                key = self._asset_key(slot)
                if key in self.assets:
                    continue
                size = slot["size"]
                self.assets[key] = self.gym.create_box(
                    self.sim,
                    float(size[0]),
                    float(size[1]),
                    float(size[2]),
                    asset_options,
                )

        self.assets[self.INACTIVE_TYPE] = self.gym.create_box(
            self.sim,
            0.02,
            0.02,
            0.02,
            asset_options,
        )

    def create_obstacles_for_env(self, env_handle, env_id, env_origin):
        if not self.enabled:
            return

        if not self.assets:
            raise RuntimeError("Dynamic obstacle assets must be created first")
        if env_id < 0 or env_id >= self.num_envs:
            raise ValueError(
                "env_id {} is outside [0, {})".format(env_id, self.num_envs)
            )

        layout_id, layout = self._select_layout_for_env(env_id)
        slots = self._expand_layout(layout)
        self.layout_ids[env_id] = layout_id
        self.actor_slots_by_env[env_id] = slots

        for actor_slot, slot in enumerate(slots):
            self._configure_actor_slot(env_id, actor_slot, env_origin, slot)
            self._create_actor(
                env_handle,
                env_id,
                actor_slot,
                self.assets[self._asset_key(slot)],
                self._actor_name(slot, actor_slot),
                self._pose_from_position(
                    self.base_positions[env_id, actor_slot],
                    self.current_orientations[env_id, actor_slot],
                ),
                active=True,
            )

        for actor_slot in range(len(slots), self.num_obstacles_per_env):
            self._configure_inactive_slot(env_id, actor_slot, env_origin)
            self._create_actor(
                env_handle,
                env_id,
                actor_slot,
                self.assets[self.INACTIVE_TYPE],
                "dynamic_inactive_{}".format(actor_slot),
                self._pose_from_position(self.base_positions[env_id, actor_slot]),
                active=False,
            )

    def bind_root_state_tensor(self, root_states):
        self.root_states = root_states
        if self.enabled:
            self._require_actor_indices()
            self.reset(self.all_env_ids, t=0.0)

    def reset(self, env_ids, t=0.0):
        if not self.enabled or self.root_states is None or len(env_ids) == 0:
            return

        env_ids = env_ids.to(device=self.device, dtype=torch.long)
        self._validate_env_ids(env_ids)
        self._require_actor_indices(env_ids)
        self._sample_motion_parameters(env_ids)

        self.reset_times[env_ids] = float(t)
        positions, velocities, orientations, angular_velocities = self._compute_motion(
            env_ids, float(t)
        )
        self._write_actor_states(
            env_ids, positions, velocities, orientations, angular_velocities
        )

    def update(self, t):
        if not self.enabled or self.root_states is None:
            return

        positions, velocities, orientations, angular_velocities = self._compute_motion(
            self.all_env_ids, float(t)
        )
        self._write_actor_states(
            self.all_env_ids, positions, velocities, orientations, angular_velocities
        )

    def get_state(self):
        if not self.enabled:
            return {}

        return {
            "suite": self.cfg.suite if self.use_suites else None,
            "use_suites": self.use_suites,
            "layout_id": self.layout_ids,
            "actor_indices": self.actor_indices,
            "actor_types": self.actor_type_names,
            "current_position": self.current_positions,
            "current_velocity": self.current_velocities,
            "current_orientation": self.current_orientations,
            "current_angular_velocity": self.current_angular_velocities,
            "base_position": self.base_positions,
            "amplitude": self.amplitudes,
            "frequency": self.frequencies,
            "phase": self.phases,
            "active_mask": self.active_mask,
            "current_offset": self.current_offsets,
            "current_gap_offset": self.current_offsets,
            "current_step_height": self.current_step_heights,
            "current_ramp_angle": self.current_ramp_angles,
        }

    def _compute_motion(self, env_ids, t):
        if self.use_suites or self.cfg.type in self.SUPPORTED_TYPES:
            return self._update_all_actor_slots(env_ids, t)
        raise ValueError(
            "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                self.cfg.type, self.SUPPORTED_TYPES
            )
        )

    def _update_all_actor_slots(self, env_ids, t):
        raw_offset, raw_velocity = self._compute_sinusoid(env_ids, t)
        motion_multipliers = self.motion_multipliers[env_ids]
        offset = raw_offset * motion_multipliers
        velocity = raw_velocity * motion_multipliers
        active = self.active_mask[env_ids]
        axis_ids = self.axis_ids[env_ids]
        ramp_mask = active & self._actor_type_mask(env_ids, "time_varying_ramp")
        linear_motion_mask = active & ~ramp_mask

        positions = self.base_positions[env_ids].clone()
        velocities = torch.zeros_like(positions)
        orientations, angular_velocities = self._fixed_orientation(env_ids)

        for axis_id in [0, 1, 2]:
            mask = linear_motion_mask & (axis_ids == axis_id)
            position_axis = positions[:, :, axis_id]
            velocity_axis = velocities[:, :, axis_id]
            position_axis[mask] = position_axis[mask] + offset[mask]
            velocity_axis[mask] = velocity[mask]
            positions[:, :, axis_id] = position_axis
            velocities[:, :, axis_id] = velocity_axis

        if torch.any(ramp_mask):
            ramp_angles = self.base_ramp_pitches[env_ids] + offset
            half_angles = 0.5 * ramp_angles
            orientation_w = orientations[:, :, 3]
            orientation_w[ramp_mask] = torch.cos(half_angles[ramp_mask])
            orientations[:, :, 3] = orientation_w

            for ramp_axis_id in [0, 1]:
                axis_ramp_mask = ramp_mask & (axis_ids == ramp_axis_id)
                if not torch.any(axis_ramp_mask):
                    continue
                orientation_axis = orientations[:, :, ramp_axis_id]
                angular_velocity_axis = angular_velocities[:, :, ramp_axis_id]
                orientation_axis[axis_ramp_mask] = torch.sin(
                    half_angles[axis_ramp_mask]
                )
                angular_velocity_axis[axis_ramp_mask] = velocity[axis_ramp_mask]
                orientations[:, :, ramp_axis_id] = orientation_axis
                angular_velocities[:, :, ramp_axis_id] = angular_velocity_axis

        return positions, velocities, orientations, angular_velocities

    def _compute_sinusoid(self, env_ids, t):
        elapsed = t - self.reset_times[env_ids]
        angle = (
            2.0 * math.pi * self.frequencies[env_ids] * elapsed + self.phases[env_ids]
        )
        offset = self.amplitudes[env_ids] * torch.sin(angle)
        velocity = (
            self.amplitudes[env_ids]
            * 2.0
            * math.pi
            * self.frequencies[env_ids]
            * torch.cos(angle)
        )
        offset = offset * self.active_mask[env_ids]
        velocity = velocity * self.active_mask[env_ids]
        return offset, velocity

    def _write_actor_states(
        self, env_ids, positions, velocities, orientations, angular_velocities
    ):
        actor_indices = self.actor_indices[env_ids].reshape(-1)
        valid_mask = actor_indices >= 0
        if not torch.any(valid_mask):
            return

        actor_indices = actor_indices[valid_mask]
        positions = positions.reshape(-1, 3)[valid_mask]
        velocities = velocities.reshape(-1, 3)[valid_mask]
        orientations = orientations.reshape(-1, 4)[valid_mask]
        angular_velocities = angular_velocities.reshape(-1, 3)[valid_mask]

        with torch.no_grad():
            self.root_states[actor_indices, 0:3] = positions
            self.root_states[actor_indices, 3:7] = orientations
            self.root_states[actor_indices, 7:10] = velocities
            self.root_states[actor_indices, 10:13] = angular_velocities

        actor_indices_int32 = actor_indices.to(dtype=torch.int32)
        self.gym.set_actor_root_state_tensor_indexed(
            self.sim,
            gymtorch.unwrap_tensor(self.root_states),
            gymtorch.unwrap_tensor(actor_indices_int32),
            len(actor_indices_int32),
        )

        self.current_positions[env_ids] = positions.view(
            len(env_ids), self.num_obstacles_per_env, 3
        )
        self.current_velocities[env_ids] = velocities.view(
            len(env_ids), self.num_obstacles_per_env, 3
        )
        self.current_orientations[env_ids] = orientations.view(
            len(env_ids), self.num_obstacles_per_env, 4
        )
        self.current_angular_velocities[env_ids] = angular_velocities.view(
            len(env_ids), self.num_obstacles_per_env, 3
        )
        self._update_type_specific_state(env_ids)

    def _validate_cfg(self):
        if self.num_envs <= 0:
            raise ValueError("DynamicObstacleManager requires num_envs > 0")
        if self.use_suites:
            if self.cfg.suite not in DYNAMIC_TERRAIN_SUITES:
                raise ValueError(
                    "Unknown dynamic terrain suite '{}'. Supported suites are {}.".format(
                        self.cfg.suite, suite_names()
                    )
                )
            layouts = get_suite_layouts(self.cfg.suite)
            if self.cfg.layout_id < 0 or self.cfg.layout_id >= len(layouts):
                raise ValueError(
                    "dynamic_obstacles.layout_id must be in [0, {}) for suite {}".format(
                        len(layouts), self.cfg.suite
                    )
                )
            for layout in layouts:
                self._validate_layout(layout)
            return

        if self.cfg.type not in self.SUPPORTED_TYPES:
            raise ValueError(
                "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                    self.cfg.type, self.SUPPORTED_TYPES
                )
            )
        expected = self._primitive_actor_count(self.cfg.type)
        if self.cfg.num_obstacles_per_env not in [1, expected]:
            raise NotImplementedError(
                "{} currently supports {} derived obstacle actor(s) per env".format(
                    self.cfg.type, expected
                )
            )
        self._validate_layout(self._primitive_layout())

    def _validate_layout(self, layout):
        if "obstacles" not in layout:
            raise ValueError("dynamic terrain layout must define obstacles")
        for obstacle in layout["obstacles"]:
            obstacle_type = obstacle["type"]
            if obstacle_type not in self.SUPPORTED_TYPES:
                raise ValueError(
                    "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                        obstacle_type, self.SUPPORTED_TYPES
                    )
                )
            if obstacle["actor_count"] != self._primitive_actor_count(obstacle_type):
                raise ValueError(
                    "layout obstacle '{}' has wrong actor_count".format(
                        obstacle.get("name", obstacle_type)
                    )
                )
            self._validate_range(obstacle["amplitude_range"], "amplitude_range")
            self._validate_range(obstacle["frequency_range"], "frequency_range")
            self._validate_range(obstacle["phase_range"], "phase_range")
            if obstacle["frequency_range"][0] < 0:
                raise ValueError(
                    "dynamic obstacle frequency ranges must be non-negative"
                )
            for value in obstacle["size"]:
                if value <= 0:
                    raise ValueError("dynamic obstacle sizes must be positive")
            if obstacle_type in ["moving_hurdle", "shifting_gap"]:
                if obstacle["motion_axis"] not in ["x", "y"]:
                    raise ValueError("motion_axis must be 'x' or 'y'")
            if obstacle_type == "shifting_gap" and obstacle["edge_separation"] <= 0:
                raise ValueError("gap edge separation must be positive")
            if obstacle_type == "shifting_gap" and obstacle.get(
                "gap_motion", "translate"
            ) not in ["translate", "width"]:
                raise ValueError("gap_motion must be 'translate' or 'width'")
            if obstacle_type == "time_varying_ramp" and obstacle.get(
                "motion_axis", "pitch"
            ) not in ["pitch", "roll"]:
                raise ValueError("ramp motion_axis must be 'pitch' or 'roll'")

    def _validate_range(self, value_range, name):
        if len(value_range) != 2:
            raise ValueError("dynamic_obstacles.{} must have two values".format(name))
        if value_range[0] > value_range[1]:
            raise ValueError(
                "dynamic_obstacles.{} lower bound must be <= upper bound".format(name)
            )

    def _validate_env_ids(self, env_ids):
        if torch.any(env_ids < 0) or torch.any(env_ids >= self.num_envs):
            raise ValueError("dynamic obstacle env_ids are outside the valid range")

    def _require_actor_indices(self, env_ids=None):
        indices = self.actor_indices if env_ids is None else self.actor_indices[env_ids]
        if torch.any(indices < 0):
            raise RuntimeError(
                "dynamic obstacle actor indices are not fully initialized"
            )

    def _possible_layouts(self):
        if self.use_suites:
            return self.suite_layouts
        return [self._primitive_layout()]

    def _primitive_layout(self):
        cfg = self.cfg
        if cfg.type == "moving_hurdle":
            obstacle = {
                "name": "primitive_moving_hurdle",
                "type": "moving_hurdle",
                "actor_count": 1,
                "base_position": [
                    cfg.base_position_x,
                    cfg.base_position_y,
                    cfg.base_position_z,
                ],
                "size": [cfg.hurdle_length, cfg.hurdle_thickness, cfg.hurdle_height],
                "motion_axis": cfg.motion_axis,
                "amplitude_range": cfg.amplitude_range,
                "frequency_range": cfg.frequency_range,
                "phase_range": cfg.phase_range,
            }
        elif cfg.type == "shifting_gap":
            obstacle = {
                "name": "primitive_shifting_gap",
                "type": "shifting_gap",
                "actor_count": 2,
                "base_position": [
                    cfg.gap_base_position_x,
                    cfg.gap_base_position_y,
                    cfg.gap_base_position_z,
                ],
                "size": [
                    cfg.gap_edge_length,
                    cfg.gap_edge_width,
                    cfg.gap_edge_height,
                ],
                "motion_axis": cfg.gap_motion_axis,
                "edge_separation": cfg.gap_edge_separation,
                "amplitude_range": cfg.gap_amplitude_range,
                "frequency_range": cfg.gap_frequency_range,
                "phase_range": cfg.gap_phase_range,
            }
        elif cfg.type == "changing_step_height":
            obstacle = {
                "name": "primitive_changing_step_height",
                "type": "changing_step_height",
                "actor_count": 1,
                "base_position": [
                    cfg.step_base_position_x,
                    cfg.step_base_position_y,
                    cfg.step_base_position_z,
                ],
                "size": [cfg.step_length, cfg.step_width, cfg.step_height],
                "motion_axis": "z",
                "amplitude_range": cfg.step_height_amplitude_range,
                "frequency_range": cfg.step_frequency_range,
                "phase_range": cfg.step_phase_range,
                "step_height": cfg.step_height,
            }
        elif cfg.type == "time_varying_ramp":
            obstacle = {
                "name": "primitive_time_varying_ramp",
                "type": "time_varying_ramp",
                "actor_count": 1,
                "base_position": [
                    cfg.ramp_base_position_x,
                    cfg.ramp_base_position_y,
                    cfg.ramp_base_position_z,
                ],
                "size": [cfg.ramp_length, cfg.ramp_width, cfg.ramp_thickness],
                "motion_axis": "pitch",
                "base_pitch": cfg.ramp_base_pitch,
                "amplitude_range": cfg.ramp_pitch_amplitude_range,
                "frequency_range": cfg.ramp_frequency_range,
                "phase_range": cfg.ramp_phase_range,
            }
        else:
            raise ValueError(
                "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                    cfg.type, self.SUPPORTED_TYPES
                )
            )
        return {"name": "primitive_{}".format(cfg.type), "obstacles": [obstacle]}

    def _select_layout_for_env(self, env_id):
        if not self.use_suites:
            return 0, self._primitive_layout()
        if self.cfg.layout_randomization:
            layout_id = int(torch.randint(len(self.suite_layouts), (1,)).item())
        else:
            layout_id = int(self.cfg.layout_id)
        return layout_id, self.suite_layouts[layout_id]

    def _expand_layout(self, layout):
        slots = []
        group_id = 0
        for obstacle in layout["obstacles"]:
            obstacle_type = obstacle["type"]
            if obstacle_type == "shifting_gap":
                axis_id = self._axis_id(obstacle["motion_axis"])
                edge_offset = 0.5 * obstacle["edge_separation"]
                gap_motion = obstacle.get("gap_motion", "translate")
                motion_multipliers = (
                    [-1.0, 1.0] if gap_motion == "width" else [1.0, 1.0]
                )
                for edge_id, signed_offset in enumerate([-edge_offset, edge_offset]):
                    base_position = list(obstacle["base_position"])
                    base_position[axis_id] += signed_offset
                    slot = dict(obstacle)
                    slot["name"] = "{}_edge_{}".format(obstacle["name"], edge_id)
                    slot["base_position"] = base_position
                    slot["group_id"] = group_id
                    slot["motion_group_id"] = group_id
                    slot["motion_multiplier"] = motion_multipliers[edge_id]
                    slots.append(slot)
            else:
                slot = dict(obstacle)
                slot["group_id"] = group_id
                slot["motion_group_id"] = group_id
                slot["motion_multiplier"] = 1.0
                slots.append(slot)
            group_id += 1
        return slots

    def _configure_actor_slot(self, env_id, actor_slot, env_origin, slot):
        base_position = self._base_position(env_origin, slot["base_position"])
        self.base_positions[env_id, actor_slot] = base_position
        self.current_positions[env_id, actor_slot] = base_position
        self.axis_ids[env_id, actor_slot] = self._slot_axis_id(slot)
        self.base_ramp_pitches[env_id, actor_slot] = float(slot.get("base_pitch", 0.0))
        self.step_heights[env_id, actor_slot] = float(slot.get("step_height", 0.0))
        self.motion_multipliers[env_id, actor_slot] = float(
            slot.get("motion_multiplier", 1.0)
        )
        self.active_mask[env_id, actor_slot] = True
        self.motion_group_ids[env_id, actor_slot] = int(
            slot.get("motion_group_id", slot["group_id"])
        )
        self.actor_type_names[env_id][actor_slot] = slot["type"]
        if slot["type"] == "time_varying_ramp":
            self.current_orientations[env_id, actor_slot] = self._axis_angle_quat(
                float(slot.get("base_pitch", 0.0)),
                self.axis_ids[env_id, actor_slot].item(),
            )

    def _configure_inactive_slot(self, env_id, actor_slot, env_origin):
        position = self._base_position(env_origin, [0.0, 0.0, -10.0])
        self.base_positions[env_id, actor_slot] = position
        self.current_positions[env_id, actor_slot] = position
        self.current_orientations[env_id, actor_slot] = self.identity_quat
        self.motion_multipliers[env_id, actor_slot] = 0.0
        self.actor_type_names[env_id][actor_slot] = self.INACTIVE_TYPE

    def _sample_motion_parameters(self, env_ids):
        for env_id in env_ids.tolist():
            group_ids = self.motion_group_ids[env_id]
            type_motion = {}
            for group_id in torch.unique(group_ids[group_ids >= 0]).tolist():
                mask = group_ids == group_id
                slot_index = int(torch.nonzero(mask, as_tuple=False)[0].item())
                slot = self.actor_slots_by_env[env_id][slot_index]
                slot_type = slot["type"]
                if slot_type not in type_motion:
                    type_motion[slot_type] = self._motion_parameters_for_slot(slot)
                amplitude, frequency = type_motion[slot_type]
                self.amplitudes[env_id, mask] = amplitude
                self.frequencies[env_id, mask] = frequency
                self.phases[env_id, mask] = self._range_value(slot["phase_range"])
            inactive_mask = group_ids < 0
            self.amplitudes[env_id, inactive_mask] = 0.0
            self.frequencies[env_id, inactive_mask] = 0.0
            self.phases[env_id, inactive_mask] = 0.0

    def _motion_parameters_for_slot(self, slot):
        return (
            self._range_value(slot["amplitude_range"]),
            self._range_value(slot["frequency_range"]),
        )

    def _create_actor(self, env_handle, env_id, actor_slot, asset, name, pose, active):
        collision_filter = self._collision_filter(active)
        handle = self.gym.create_actor(
            env_handle,
            asset,
            pose,
            name,
            env_id,
            collision_filter,
            0,
        )
        actor_index = self.gym.get_actor_index(env_handle, handle, gymapi.DOMAIN_SIM)
        self.actor_indices[env_id, actor_slot] = actor_index
        return handle

    def _asset_key(self, slot):
        size = tuple(round(float(value), 4) for value in slot["size"])
        return "{}_{}".format(slot["type"], size)

    def _actor_name(self, slot, actor_slot):
        names = {
            "moving_hurdle": "dynamic_hurdle",
            "shifting_gap": "dynamic_gap_edge",
            "changing_step_height": "dynamic_step",
            "time_varying_ramp": "dynamic_ramp",
        }
        return "{}_{}".format(names[slot["type"]], actor_slot)

    def _num_obstacles_for_mode(self):
        if self.use_suites:
            if self.cfg.layout_randomization:
                return max_suite_actor_count(self.cfg.suite)
            return layout_actor_count(self.suite_layouts[int(self.cfg.layout_id)])
        return self._primitive_actor_count(self.cfg.type)

    def _primitive_actor_count(self, obstacle_type):
        if obstacle_type == "shifting_gap":
            return 2
        if obstacle_type in (
            "moving_hurdle",
            "changing_step_height",
            "time_varying_ramp",
        ):
            return 1
        raise ValueError(
            "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                obstacle_type, self.SUPPORTED_TYPES
            )
        )

    def _asset_density(self):
        return float(getattr(self.cfg, "asset_density", self.cfg.hurdle_asset_density))

    def _axis_id(self, axis):
        axis_ids = {"x": 0, "roll": 0, "y": 1, "pitch": 1, "z": 2}
        if axis not in axis_ids:
            raise ValueError("unknown dynamic obstacle axis '{}'".format(axis))
        return axis_ids[axis]

    def _slot_axis_id(self, slot):
        if slot["type"] == "changing_step_height":
            return 2
        if slot["type"] == "time_varying_ramp":
            return self._axis_id(slot.get("motion_axis", "pitch"))
        return self._axis_id(slot["motion_axis"])

    def _actor_type_mask(self, env_ids, actor_type):
        mask = torch.zeros(
            len(env_ids),
            self.num_obstacles_per_env,
            dtype=torch.bool,
            device=self.device,
        )
        for local_id, env_id in enumerate(env_ids.tolist()):
            for actor_slot, slot_type in enumerate(self.actor_type_names[env_id]):
                mask[local_id, actor_slot] = slot_type == actor_type
        return mask

    def _uniform(self, value_range, shape):
        low, high = value_range
        return torch.empty(shape, dtype=torch.float, device=self.device).uniform_(
            float(low), float(high)
        )

    def _range_value(self, value_range):
        if self.cfg.randomize_on_reset:
            return self._uniform(value_range, (1,)).item()
        return sum(value_range) / 2.0

    def _fixed_orientation(self, env_ids):
        orientations = torch.zeros(
            len(env_ids),
            self.num_obstacles_per_env,
            4,
            dtype=torch.float,
            device=self.device,
        )
        orientations[:, :, 3] = 1.0
        angular_velocities = torch.zeros(
            len(env_ids),
            self.num_obstacles_per_env,
            3,
            dtype=torch.float,
            device=self.device,
        )
        return orientations, angular_velocities

    def _base_position(self, env_origin, local_position):
        origin = (
            env_origin.detach().cpu() if torch.is_tensor(env_origin) else env_origin
        )
        return torch.tensor(
            [
                float(origin[0]) + float(local_position[0]),
                float(origin[1]) + float(local_position[1]),
                float(origin[2]) + float(local_position[2]),
            ],
            dtype=torch.float,
            device=self.device,
        )

    def _pose_from_position(self, position, orientation=None):
        pose = gymapi.Transform()
        pose.p = gymapi.Vec3(position[0].item(), position[1].item(), position[2].item())
        if orientation is None:
            pose.r = gymapi.Quat(0.0, 0.0, 0.0, 1.0)
        else:
            pose.r = gymapi.Quat(
                orientation[0].item(),
                orientation[1].item(),
                orientation[2].item(),
                orientation[3].item(),
            )
        return pose

    def _collision_filter(self, active=True):
        if not active:
            return 1
        return 0 if self.cfg.collision_enabled else 1

    def _axis_angle_quat(self, angle, axis_id):
        half_angle = 0.5 * angle
        quat = [0.0, 0.0, 0.0, math.cos(half_angle)]
        quat[int(axis_id)] = math.sin(half_angle)
        return torch.tensor(
            quat,
            dtype=torch.float,
            device=self.device,
        )

    def _update_type_specific_state(self, env_ids):
        delta = self.current_positions[env_ids] - self.base_positions[env_ids]
        current_offsets = torch.zeros_like(self.current_offsets[env_ids])
        for axis_id in [0, 1, 2]:
            mask = self.axis_ids[env_ids] == axis_id
            current_offsets[mask] = delta[:, :, axis_id][mask]
        self.current_offsets[env_ids] = current_offsets

        step_mask = self._actor_type_mask(env_ids, "changing_step_height")
        ramp_mask = self._actor_type_mask(env_ids, "time_varying_ramp")

        current_step_heights = torch.zeros_like(self.current_step_heights[env_ids])
        if torch.any(step_mask):
            heights = (
                self.current_positions[env_ids, :, 2] + 0.5 * self.step_heights[env_ids]
            )
            current_step_heights[step_mask] = heights[step_mask]
        self.current_step_heights[env_ids] = current_step_heights

        current_ramp_angles = torch.zeros_like(self.current_ramp_angles[env_ids])
        if torch.any(ramp_mask):
            ramp_axis = torch.gather(
                self.current_orientations[env_ids, :, 0:3],
                2,
                self.axis_ids[env_ids].unsqueeze(-1),
            ).squeeze(-1)
            ramp_angles = 2.0 * torch.atan2(
                ramp_axis,
                self.current_orientations[env_ids, :, 3],
            )
            current_ramp_angles[ramp_mask] = ramp_angles[ramp_mask]
        self.current_ramp_angles[env_ids] = current_ramp_angles
