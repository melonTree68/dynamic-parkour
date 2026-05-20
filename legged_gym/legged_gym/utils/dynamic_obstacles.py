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
        if cfg.type != "moving_hurdle":
            raise NotImplementedError(
                "{} is planned but not implemented yet".format(cfg.type)
            )
        if cfg.motion_axis not in ["x", "y"]:
            raise ValueError("dynamic_obstacles.motion_axis must be 'x' or 'y'")

        self._validate_cfg()
        self.num_obstacles_per_env = cfg.num_obstacles_per_env
        self.axis_id = 0 if cfg.motion_axis == "x" else 1
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
        self.amplitudes = torch.zeros(
            num_envs, self.num_obstacles_per_env, dtype=torch.float, device=device
        )
        self.frequencies = torch.zeros_like(self.amplitudes)
        self.phases = torch.zeros_like(self.amplitudes)
        self.reset_times = torch.zeros_like(self.amplitudes)
        self.hurdle_asset = None

    def create_assets(self):
        if not self.enabled:
            return

        asset_options = gymapi.AssetOptions()
        asset_options.density = self.cfg.hurdle_asset_density
        asset_options.disable_gravity = True
        asset_options.fix_base_link = bool(self.cfg.make_kinematic)
        asset_options.thickness = 0.01

        self.hurdle_asset = self.gym.create_box(
            self.sim,
            self.cfg.hurdle_length,
            self.cfg.hurdle_thickness,
            self.cfg.hurdle_height,
            asset_options,
        )

    def create_obstacles_for_env(self, env_handle, env_id, env_origin):
        if not self.enabled:
            return

        if self.hurdle_asset is None:
            raise RuntimeError("Dynamic obstacle assets must be created first")
        if env_id < 0 or env_id >= self.num_envs:
            raise ValueError("env_id {} is outside [0, {})".format(env_id, self.num_envs))

        # base_position_* are local offsets from the static terrain env origin.
        # x=2.0 places the MVP hurdle shortly after the robot start platform,
        # while keeping the static parkour goals and heightfield unchanged.
        origin = env_origin.detach().cpu() if torch.is_tensor(env_origin) else env_origin
        base_position = torch.tensor(
            [
                float(origin[0]) + self.cfg.base_position_x,
                float(origin[1]) + self.cfg.base_position_y,
                float(origin[2]) + self.cfg.base_position_z,
            ],
            dtype=torch.float,
            device=self.device,
        )
        self.base_positions[env_id, 0] = base_position
        self.current_positions[env_id, 0] = base_position

        pose = gymapi.Transform()
        pose.p = gymapi.Vec3(
            base_position[0].item(),
            base_position[1].item(),
            base_position[2].item(),
        )
        pose.r = gymapi.Quat(0.0, 0.0, 0.0, 1.0)

        # Isaac Gym collision filters are bitmasks. The enabled path uses zero
        # to allow normal same-env collision; the disabled-collision path is a
        # best-effort scaffold for later validation in the viewer.
        collision_filter = 0 if self.cfg.collision_enabled else 1
        handle = self.gym.create_actor(
            env_handle,
            self.hurdle_asset,
            pose,
            "dynamic_hurdle",
            env_id,
            collision_filter,
            0,
        )
        actor_index = self.gym.get_actor_index(env_handle, handle, gymapi.DOMAIN_SIM)
        self.actor_handles[env_id].append(handle)
        self.actor_indices[env_id, 0] = actor_index

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
        if self.cfg.randomize_on_reset:
            self.amplitudes[env_ids] = self._uniform(
                self.cfg.amplitude_range, (len(env_ids), self.num_obstacles_per_env)
            )
            self.frequencies[env_ids] = self._uniform(
                self.cfg.frequency_range, (len(env_ids), self.num_obstacles_per_env)
            )
            self.phases[env_ids] = self._uniform(
                self.cfg.phase_range, (len(env_ids), self.num_obstacles_per_env)
            )
        else:
            self.amplitudes[env_ids] = sum(self.cfg.amplitude_range) / 2.0
            self.frequencies[env_ids] = sum(self.cfg.frequency_range) / 2.0
            self.phases[env_ids] = 0.0

        self.reset_times[env_ids] = float(t)
        positions, velocities = self._compute_motion(env_ids, float(t))
        self._write_actor_states(env_ids, positions, velocities)

    def update(self, t):
        if not self.enabled or self.root_states is None:
            return

        positions, velocities = self._compute_motion(self.all_env_ids, float(t))
        self._write_actor_states(self.all_env_ids, positions, velocities)

    def get_state(self):
        if not self.enabled:
            return {}

        return {
            "current_position": self.current_positions,
            "current_velocity": self.current_velocities,
            "base_position": self.base_positions,
            "amplitude": self.amplitudes,
            "frequency": self.frequencies,
            "phase": self.phases,
            "actor_indices": self.actor_indices,
        }

    def _uniform(self, value_range, shape):
        low, high = value_range
        return torch.empty(shape, dtype=torch.float, device=self.device).uniform_(
            float(low), float(high)
        )

    def _compute_motion(self, env_ids, t):
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

        positions = self.base_positions[env_ids].clone()
        velocities = torch.zeros_like(positions)
        positions[:, :, self.axis_id] += offset
        velocities[:, :, self.axis_id] = velocity
        return positions, velocities

    def _write_actor_states(self, env_ids, positions, velocities):
        actor_indices = self.actor_indices[env_ids].reshape(-1)
        valid_mask = actor_indices >= 0
        if not torch.any(valid_mask):
            return

        actor_indices = actor_indices[valid_mask]
        positions = positions.reshape(-1, 3)[valid_mask]
        velocities = velocities.reshape(-1, 3)[valid_mask]

        with torch.no_grad():
            self.root_states[actor_indices, 0:3] = positions
            self.root_states[actor_indices, 3:7] = self.identity_quat
            self.root_states[actor_indices, 7:10] = velocities
            self.root_states[actor_indices, 10:13] = self.zero_ang_vel

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

    def _validate_cfg(self):
        if self.num_envs <= 0:
            raise ValueError("DynamicObstacleManager requires num_envs > 0")
        if self.cfg.num_obstacles_per_env != 1:
            raise NotImplementedError(
                "moving_hurdle currently supports exactly one obstacle per env"
            )
        for name in ["amplitude_range", "frequency_range", "phase_range"]:
            value = getattr(self.cfg, name)
            if len(value) != 2:
                raise ValueError("dynamic_obstacles.{} must have two values".format(name))
            if value[0] > value[1]:
                raise ValueError(
                    "dynamic_obstacles.{} lower bound must be <= upper bound".format(name)
                )
        if self.cfg.frequency_range[0] < 0:
            raise ValueError("dynamic_obstacles.frequency_range must be non-negative")
        for name in ["hurdle_length", "hurdle_thickness", "hurdle_height"]:
            if getattr(self.cfg, name) <= 0:
                raise ValueError("dynamic_obstacles.{} must be positive".format(name))
        if self.cfg.motion_axis not in ["x", "y"]:
            raise ValueError("dynamic_obstacles.motion_axis must be 'x' or 'y'")

    def _validate_env_ids(self, env_ids):
        if torch.any(env_ids < 0) or torch.any(env_ids >= self.num_envs):
            raise ValueError("dynamic obstacle env_ids are outside the valid range")

    def _require_actor_indices(self, env_ids=None):
        indices = self.actor_indices if env_ids is None else self.actor_indices[env_ids]
        if torch.any(indices < 0):
            raise RuntimeError("dynamic obstacle actor indices are not fully initialized")


class MovingHurdleObstacle:
    """Reserved name for a future per-obstacle implementation."""


class ShiftingGapObstacle:
    """TODO: moving platform or boundary actors for dynamic gaps."""


class ChangingStepObstacle:
    """TODO: changing-height box actors for step terrain."""


class TimeVaryingRampObstacle:
    """TODO: tilted rigid bodies or multi-box ramp approximation."""
