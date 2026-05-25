import math

import torch
from isaacgym import gymapi, gymtorch


class DynamicObstacleManager:
    """Create and update optional dynamic obstacle actors.

    The first implementation intentionally keeps terrain heightfields and
    triangle meshes static. Dynamic obstacles are Isaac Gym box actors whose
    root states are updated through the simulator root-state tensor.
    """

    SUPPORTED_TYPES = (
        "moving_hurdle",
        "shifting_gap",
        "changing_step_height",
        "time_varying_ramp",
    )

    def __init__(self, gym, sim, device, cfg, num_envs):
        self.gym = gym
        self.sim = sim
        self.device = device
        self.cfg = cfg
        self.num_envs = num_envs
        self.enabled = bool(getattr(cfg, "enable", False))
        self.root_states = None

        if not self.enabled:
            return

        if cfg.type not in self.SUPPORTED_TYPES:
            raise ValueError(
                "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                    cfg.type, self.SUPPORTED_TYPES
                )
            )

        self._validate_cfg()
        self.num_obstacles_per_env = self._num_obstacles_for_type(cfg.type)
        self.axis_id = self._motion_axis_id()
        self.all_env_ids = torch.arange(num_envs, dtype=torch.long, device=device)
        self.identity_quat = torch.tensor(
            [0.0, 0.0, 0.0, 1.0], dtype=torch.float, device=device
        )
        self.zero_ang_vel = torch.zeros(3, dtype=torch.float, device=device)
        self.actor_handles = [[] for _ in range(num_envs)]
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
        self.current_step_heights = torch.zeros_like(self.amplitudes)
        self.current_ramp_angles = torch.zeros_like(self.amplitudes)
        self.assets = {}

    def create_assets(self):
        if not self.enabled:
            return

        asset_options = gymapi.AssetOptions()
        asset_options.density = self._asset_density()
        asset_options.disable_gravity = True
        asset_options.fix_base_link = bool(self.cfg.make_kinematic)
        asset_options.thickness = 0.01

        if self.cfg.type == "moving_hurdle":
            self.assets["moving_hurdle"] = self.gym.create_box(
                self.sim,
                self.cfg.hurdle_length,
                self.cfg.hurdle_thickness,
                self.cfg.hurdle_height,
                asset_options,
            )
        elif self.cfg.type == "shifting_gap":
            self.assets["shifting_gap_edge"] = self.gym.create_box(
                self.sim,
                self.cfg.gap_edge_length,
                self.cfg.gap_edge_width,
                self.cfg.gap_edge_height,
                asset_options,
            )
        elif self.cfg.type == "changing_step_height":
            self.assets["changing_step_height"] = self.gym.create_box(
                self.sim,
                self.cfg.step_length,
                self.cfg.step_width,
                self.cfg.step_height,
                asset_options,
            )
        elif self.cfg.type == "time_varying_ramp":
            self.assets["time_varying_ramp"] = self.gym.create_box(
                self.sim,
                self.cfg.ramp_length,
                self.cfg.ramp_width,
                self.cfg.ramp_thickness,
                asset_options,
            )
        else:
            raise ValueError(
                "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                    self.cfg.type, self.SUPPORTED_TYPES
                )
            )

    def create_obstacles_for_env(self, env_handle, env_id, env_origin):
        if not self.enabled:
            return

        if not self.assets:
            raise RuntimeError("Dynamic obstacle assets must be created first")
        if env_id < 0 or env_id >= self.num_envs:
            raise ValueError("env_id {} is outside [0, {})".format(env_id, self.num_envs))

        if self.cfg.type == "moving_hurdle":
            self._create_moving_hurdle(env_handle, env_id, env_origin)
        elif self.cfg.type == "shifting_gap":
            self._create_shifting_gap(env_handle, env_id, env_origin)
        elif self.cfg.type == "changing_step_height":
            self._create_changing_step_height(env_handle, env_id, env_origin)
        elif self.cfg.type == "time_varying_ramp":
            self._create_time_varying_ramp(env_handle, env_id, env_origin)
        else:
            raise ValueError(
                "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                    self.cfg.type, self.SUPPORTED_TYPES
                )
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
            "current_position": self.current_positions,
            "current_velocity": self.current_velocities,
            "current_orientation": self.current_orientations,
            "current_angular_velocity": self.current_angular_velocities,
            "base_position": self.base_positions,
            "amplitude": self.amplitudes,
            "frequency": self.frequencies,
            "phase": self.phases,
            "current_offset": self.current_offsets,
            "current_gap_offset": self.current_offsets,
            "current_step_height": self.current_step_heights,
            "current_ramp_angle": self.current_ramp_angles,
            "actor_indices": self.actor_indices,
        }

    def _uniform(self, value_range, shape):
        low, high = value_range
        return torch.empty(shape, dtype=torch.float, device=self.device).uniform_(
            float(low), float(high)
        )

    def _compute_motion(self, env_ids, t):
        if self.cfg.type == "moving_hurdle":
            return self._update_moving_hurdle(env_ids, t)
        if self.cfg.type == "shifting_gap":
            return self._update_shifting_gap(env_ids, t)
        if self.cfg.type == "changing_step_height":
            return self._update_changing_step_height(env_ids, t)
        if self.cfg.type == "time_varying_ramp":
            return self._update_time_varying_ramp(env_ids, t)
        raise ValueError(
            "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                self.cfg.type, self.SUPPORTED_TYPES
            )
        )

    def _compute_sinusoid(self, env_ids, t):
        elapsed = t - self.reset_times[env_ids]
        angle = 2.0 * math.pi * self.frequencies[env_ids] * elapsed + self.phases[env_ids]
        offset = self.amplitudes[env_ids] * torch.sin(angle)
        velocity = (
            self.amplitudes[env_ids]
            * 2.0
            * math.pi
            * self.frequencies[env_ids]
            * torch.cos(angle)
        )
        return offset, velocity

    def _update_moving_hurdle(self, env_ids, t):
        offset, velocity = self._compute_sinusoid(env_ids, t)
        positions = self.base_positions[env_ids].clone()
        velocities = torch.zeros_like(positions)
        positions[:, :, self.axis_id] += offset
        velocities[:, :, self.axis_id] = velocity
        orientations, angular_velocities = self._fixed_orientation(env_ids)
        return positions, velocities, orientations, angular_velocities

    def _update_shifting_gap(self, env_ids, t):
        offset, velocity = self._compute_sinusoid(env_ids, t)
        positions = self.base_positions[env_ids].clone()
        velocities = torch.zeros_like(positions)
        positions[:, :, self.axis_id] += offset
        velocities[:, :, self.axis_id] = velocity
        orientations, angular_velocities = self._fixed_orientation(env_ids)
        return positions, velocities, orientations, angular_velocities

    def _update_changing_step_height(self, env_ids, t):
        offset, velocity = self._compute_sinusoid(env_ids, t)
        positions = self.base_positions[env_ids].clone()
        velocities = torch.zeros_like(positions)
        positions[:, :, 2] += offset
        velocities[:, :, 2] = velocity
        orientations, angular_velocities = self._fixed_orientation(env_ids)
        return positions, velocities, orientations, angular_velocities

    def _update_time_varying_ramp(self, env_ids, t):
        offset, angular_velocity_y = self._compute_sinusoid(env_ids, t)
        ramp_angles = float(self.cfg.ramp_base_pitch) + offset
        half_angles = 0.5 * ramp_angles
        orientations = torch.zeros(
            len(env_ids),
            self.num_obstacles_per_env,
            4,
            dtype=torch.float,
            device=self.device,
        )
        orientations[:, :, 1] = torch.sin(half_angles)
        orientations[:, :, 3] = torch.cos(half_angles)
        positions = self.base_positions[env_ids].clone()
        velocities = torch.zeros_like(positions)
        angular_velocities = torch.zeros_like(positions)
        angular_velocities[:, :, 1] = angular_velocity_y
        return positions, velocities, orientations, angular_velocities

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
        expected = self._num_obstacles_for_type(self.cfg.type)
        if self.cfg.num_obstacles_per_env not in [1, expected]:
            raise NotImplementedError(
                "{} currently supports {} derived obstacle actor(s) per env".format(
                    self.cfg.type, expected
                )
            )

        if self.cfg.type == "moving_hurdle":
            self._validate_axis("motion_axis")
            self._validate_ranges("amplitude_range", "frequency_range", "phase_range")
            self._validate_positive(
                "hurdle_length", "hurdle_thickness", "hurdle_height"
            )
        elif self.cfg.type == "shifting_gap":
            self._validate_axis("gap_motion_axis")
            self._validate_ranges(
                "gap_amplitude_range", "gap_frequency_range", "gap_phase_range"
            )
            self._validate_positive(
                "gap_edge_length",
                "gap_edge_width",
                "gap_edge_height",
                "gap_edge_separation",
            )
        elif self.cfg.type == "changing_step_height":
            self._validate_ranges(
                "step_height_amplitude_range",
                "step_frequency_range",
                "step_phase_range",
            )
            self._validate_positive("step_length", "step_width", "step_height")
        elif self.cfg.type == "time_varying_ramp":
            self._validate_ranges(
                "ramp_pitch_amplitude_range",
                "ramp_frequency_range",
                "ramp_phase_range",
            )
            self._validate_positive("ramp_length", "ramp_width", "ramp_thickness")
        else:
            raise ValueError(
                "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                    self.cfg.type, self.SUPPORTED_TYPES
                )
            )

    def _validate_env_ids(self, env_ids):
        if torch.any(env_ids < 0) or torch.any(env_ids >= self.num_envs):
            raise ValueError("dynamic obstacle env_ids are outside the valid range")

    def _require_actor_indices(self, env_ids=None):
        indices = self.actor_indices if env_ids is None else self.actor_indices[env_ids]
        if torch.any(indices < 0):
            raise RuntimeError("dynamic obstacle actor indices are not fully initialized")

    def _num_obstacles_for_type(self, obstacle_type):
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

    def _motion_axis_id(self):
        if self.cfg.type == "changing_step_height":
            return 2
        if self.cfg.type == "time_varying_ramp":
            return 1
        axis_name = "gap_motion_axis" if self.cfg.type == "shifting_gap" else "motion_axis"
        return 0 if getattr(self.cfg, axis_name) == "x" else 1

    def _validate_ranges(self, amplitude_name, frequency_name, phase_name):
        for name in [amplitude_name, frequency_name, phase_name]:
            value = getattr(self.cfg, name)
            if len(value) != 2:
                raise ValueError("dynamic_obstacles.{} must have two values".format(name))
            if value[0] > value[1]:
                raise ValueError(
                    "dynamic_obstacles.{} lower bound must be <= upper bound".format(name)
                )
        if getattr(self.cfg, frequency_name)[0] < 0:
            raise ValueError(
                "dynamic_obstacles.{} must be non-negative".format(frequency_name)
            )

    def _validate_positive(self, *names):
        for name in names:
            if getattr(self.cfg, name) <= 0:
                raise ValueError("dynamic_obstacles.{} must be positive".format(name))

    def _validate_axis(self, name):
        if getattr(self.cfg, name) not in ["x", "y"]:
            raise ValueError("dynamic_obstacles.{} must be 'x' or 'y'".format(name))

    def _motion_range_names(self):
        if self.cfg.type == "moving_hurdle":
            return "amplitude_range", "frequency_range", "phase_range"
        if self.cfg.type == "shifting_gap":
            return "gap_amplitude_range", "gap_frequency_range", "gap_phase_range"
        if self.cfg.type == "changing_step_height":
            return (
                "step_height_amplitude_range",
                "step_frequency_range",
                "step_phase_range",
            )
        if self.cfg.type == "time_varying_ramp":
            return (
                "ramp_pitch_amplitude_range",
                "ramp_frequency_range",
                "ramp_phase_range",
            )
        raise ValueError(
            "Unknown dynamic obstacle type '{}'. Supported types are {}.".format(
                self.cfg.type, self.SUPPORTED_TYPES
            )
        )

    def _sample_motion_parameters(self, env_ids):
        amplitude_name, frequency_name, phase_name = self._motion_range_names()
        shape = (len(env_ids), self.num_obstacles_per_env)
        shared_shape = (len(env_ids), 1)

        if self.cfg.randomize_on_reset:
            amplitude = self._uniform(getattr(self.cfg, amplitude_name), shared_shape)
            frequency = self._uniform(getattr(self.cfg, frequency_name), shared_shape)
            phase = self._uniform(getattr(self.cfg, phase_name), shared_shape)
        else:
            amplitude = torch.full(
                shared_shape,
                sum(getattr(self.cfg, amplitude_name)) / 2.0,
                dtype=torch.float,
                device=self.device,
            )
            frequency = torch.full(
                shared_shape,
                sum(getattr(self.cfg, frequency_name)) / 2.0,
                dtype=torch.float,
                device=self.device,
            )
            phase = torch.zeros(shared_shape, dtype=torch.float, device=self.device)

        self.amplitudes[env_ids] = amplitude.expand(shape)
        self.frequencies[env_ids] = frequency.expand(shape)
        self.phases[env_ids] = phase.expand(shape)

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

    def _base_position(self, env_origin, x, y, z):
        origin = env_origin.detach().cpu() if torch.is_tensor(env_origin) else env_origin
        return torch.tensor(
            [float(origin[0]) + x, float(origin[1]) + y, float(origin[2]) + z],
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

    def _collision_filter(self):
        # Isaac Gym collision filters are bitmasks. The enabled path uses zero
        # to allow normal same-env collision; the disabled-collision path is a
        # best-effort scaffold for later validation in the viewer.
        return 0 if self.cfg.collision_enabled else 1

    def _create_actor(self, env_handle, env_id, actor_slot, asset, name, pose):
        handle = self.gym.create_actor(
            env_handle,
            asset,
            pose,
            name,
            env_id,
            self._collision_filter(),
            0,
        )
        actor_index = self.gym.get_actor_index(env_handle, handle, gymapi.DOMAIN_SIM)
        self.actor_handles[env_id].append(handle)
        self.actor_indices[env_id, actor_slot] = actor_index
        return handle

    def _create_moving_hurdle(self, env_handle, env_id, env_origin):
        base_position = self._base_position(
            env_origin,
            self.cfg.base_position_x,
            self.cfg.base_position_y,
            self.cfg.base_position_z,
        )
        self.base_positions[env_id, 0] = base_position
        self.current_positions[env_id, 0] = base_position
        self._create_actor(
            env_handle,
            env_id,
            0,
            self.assets["moving_hurdle"],
            "dynamic_hurdle",
            self._pose_from_position(base_position),
        )

    def _create_shifting_gap(self, env_handle, env_id, env_origin):
        base_position = self._base_position(
            env_origin,
            self.cfg.gap_base_position_x,
            self.cfg.gap_base_position_y,
            self.cfg.gap_base_position_z,
        )
        edge_offset = 0.5 * self.cfg.gap_edge_separation
        offsets = [-edge_offset, edge_offset]
        for actor_slot, offset in enumerate(offsets):
            position = base_position.clone()
            position[self.axis_id] += offset
            self.base_positions[env_id, actor_slot] = position
            self.current_positions[env_id, actor_slot] = position
            self._create_actor(
                env_handle,
                env_id,
                actor_slot,
                self.assets["shifting_gap_edge"],
                "dynamic_gap_edge_{}".format(actor_slot),
                self._pose_from_position(position),
            )

    def _create_changing_step_height(self, env_handle, env_id, env_origin):
        base_position = self._base_position(
            env_origin,
            self.cfg.step_base_position_x,
            self.cfg.step_base_position_y,
            self.cfg.step_base_position_z,
        )
        self.base_positions[env_id, 0] = base_position
        self.current_positions[env_id, 0] = base_position
        self._create_actor(
            env_handle,
            env_id,
            0,
            self.assets["changing_step_height"],
            "dynamic_step",
            self._pose_from_position(base_position),
        )

    def _create_time_varying_ramp(self, env_handle, env_id, env_origin):
        base_position = self._base_position(
            env_origin,
            self.cfg.ramp_base_position_x,
            self.cfg.ramp_base_position_y,
            self.cfg.ramp_base_position_z,
        )
        orientation = self._pitch_quat(float(self.cfg.ramp_base_pitch))
        self.base_positions[env_id, 0] = base_position
        self.current_positions[env_id, 0] = base_position
        self.current_orientations[env_id, 0] = orientation
        self._create_actor(
            env_handle,
            env_id,
            0,
            self.assets["time_varying_ramp"],
            "dynamic_ramp",
            self._pose_from_position(base_position, orientation),
        )

    def _pitch_quat(self, pitch):
        half_pitch = 0.5 * pitch
        return torch.tensor(
            [0.0, math.sin(half_pitch), 0.0, math.cos(half_pitch)],
            dtype=torch.float,
            device=self.device,
        )

    def _update_type_specific_state(self, env_ids):
        self.current_offsets[env_ids] = (
            self.current_positions[env_ids] - self.base_positions[env_ids]
        )[:, :, self.axis_id]
        self.current_step_heights[env_ids] = (
            self.current_positions[env_ids, :, 2] + 0.5 * self.cfg.step_height
            if self.cfg.type == "changing_step_height"
            else 0.0
        )
        self.current_ramp_angles[env_ids] = (
            2.0 * torch.atan2(
                self.current_orientations[env_ids, :, 1],
                self.current_orientations[env_ids, :, 3],
            )
            if self.cfg.type == "time_varying_ramp"
            else 0.0
        )


class MovingHurdleObstacle:
    """Reserved name for a future per-obstacle implementation."""


class ShiftingGapObstacle:
    """Reserved name for a future per-obstacle implementation."""


class ChangingStepObstacle:
    """Reserved name for a future per-obstacle implementation."""


class TimeVaryingRampObstacle:
    """Reserved name for a future per-obstacle implementation."""
