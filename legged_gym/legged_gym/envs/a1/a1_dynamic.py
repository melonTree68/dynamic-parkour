import numpy as np
import torch

from isaacgym import gymapi, gymtorch
from isaacgym.torch_utils import quat_from_euler_xyz

from legged_gym.envs.base.legged_robot import LeggedRobot
from legged_gym.utils.math import quat_apply_yaw
from legged_gym.utils.terrain import (
    DYNAMIC_GAP,
    DYNAMIC_HURDLE,
    DYNAMIC_STEP,
    DYNAMIC_TILTED_PADS,
)


class DynamicLeggedRobot(LeggedRobot):
    """A1 parkour environment with scripted physical obstacle actors."""

    def __init__(self, cfg, sim_params, physics_engine, sim_device, headless):
        self.num_dynamic_obstacles = cfg.dynamic_obstacles.num_obstacles
        self.num_dynamic_slots = cfg.dynamic_obstacles.slots_per_obstacle
        self.num_actors_per_env = (
            1 + self.num_dynamic_obstacles * self.num_dynamic_slots
        )
        super().__init__(cfg, sim_params, physics_engine, sim_device, headless)

    def _prepare_additional_assets(self):
        options = gymapi.AssetOptions()
        options.disable_gravity = True
        dims = self.cfg.dynamic_obstacles.panel_dims
        self.dynamic_asset = self.gym.create_box(
            self.sim, dims[0], dims[1], dims[2], options
        )
        self.dynamic_actor_handles = []

    def _create_additional_actors(self, env_handle, env_id):
        row = int(self.terrain_levels[env_id].item())
        col = int(self.terrain_types[env_id].item())
        family = int(self.terrain.dynamic_family[row, col])
        specs = self.terrain.dynamic_obstacle_specs[row, col].reshape(-1, 7)
        handles = []
        for i in range(self.num_dynamic_obstacles * self.num_dynamic_slots):
            pose = gymapi.Transform()
            x, y, z = specs[i, :3]
            if z <= self.cfg.dynamic_obstacles.inactive_z / 2:
                x = float(self.env_origins[env_id, 0].item()) + i
                y = float(self.env_origins[env_id, 1].item()) - 4.0
                z = self.cfg.dynamic_obstacles.inactive_z - i
            elif family == DYNAMIC_HURDLE:
                z = z + specs[i, 5] / 2 - self.cfg.dynamic_obstacles.panel_dims[0] / 2
                pose.r = gymapi.Quat.from_euler_zyx(0.0, np.pi / 2, 0.0)
            pose.p = gymapi.Vec3(float(x), float(y), float(z))
            handle = self.gym.create_actor(
                env_handle,
                self.dynamic_asset,
                pose,
                "dynamic_obstacle_{}".format(i),
                env_id,
                0,
                0,
            )
            handles.append(handle)
        self.dynamic_actor_handles.append(handles)

    def _init_buffers(self):
        super()._init_buffers()
        self.obstacle_root_states = self.all_root_states[:, 1:, :].view(
            self.num_envs, self.num_dynamic_obstacles, self.num_dynamic_slots, 13
        )
        self.dynamic_family_table = torch.from_numpy(self.terrain.dynamic_family).to(
            device=self.device, dtype=torch.long
        )
        self.dynamic_difficulty_table = torch.from_numpy(
            self.terrain.dynamic_difficulty
        ).to(device=self.device, dtype=torch.float)
        self.dynamic_specs_table = torch.from_numpy(
            self.terrain.dynamic_obstacle_specs
        ).to(device=self.device, dtype=torch.float)
        self.dynamic_goal_mask_table = torch.from_numpy(
            self.terrain.dynamic_goal_mask
        ).to(device=self.device, dtype=torch.bool)

        self.dynamic_family = torch.zeros(
            self.num_envs, device=self.device, dtype=torch.long
        )
        self.dynamic_difficulty = torch.zeros(self.num_envs, device=self.device)
        self.dynamic_specs = torch.zeros(
            self.num_envs,
            self.num_dynamic_obstacles,
            self.num_dynamic_slots,
            7,
            device=self.device,
        )
        self.dynamic_goal_mask = torch.zeros(
            self.num_envs,
            self.cfg.terrain.num_goals,
            device=self.device,
            dtype=torch.bool,
        )
        self.dynamic_base_goals = torch.zeros(
            self.num_envs, self.cfg.terrain.num_goals, 3, device=self.device
        )
        self.dynamic_phase = torch.zeros(
            self.num_envs, self.num_dynamic_obstacles, device=self.device
        )
        self.dynamic_amplitude = torch.zeros_like(self.dynamic_phase)
        self.dynamic_period = torch.ones_like(self.dynamic_phase)
        self.dynamic_time = torch.zeros(self.num_envs, device=self.device)
        self.dynamic_offset = torch.zeros_like(self.dynamic_phase)
        self.dynamic_velocity = torch.zeros_like(self.dynamic_phase)

        self.dynamic_actor_indices = (
            torch.arange(self.num_envs, dtype=torch.int32, device=self.device)[:, None]
            * self.num_actors_per_env
            + torch.arange(
                1, self.num_actors_per_env, dtype=torch.int32, device=self.device
            )[None, :]
        )
        panel_dims = torch.tensor(
            self.cfg.dynamic_obstacles.panel_dims, device=self.device
        )
        self.dynamic_dims = panel_dims.repeat(self.num_envs, 1)
        hurdle = (
            self.dynamic_family_table[self.terrain_levels, self.terrain_types]
            == DYNAMIC_HURDLE
        )
        self.dynamic_dims[hurdle] = panel_dims[[2, 1, 0]]

    def _reset_additional_actors(self, env_ids):
        rows = self.terrain_levels[env_ids]
        cols = self.terrain_types[env_ids]
        self.dynamic_family[env_ids] = self.dynamic_family_table[rows, cols]
        self.dynamic_difficulty[env_ids] = self.dynamic_difficulty_table[rows, cols]
        self.dynamic_specs[env_ids] = self.dynamic_specs_table[rows, cols]
        self.dynamic_goal_mask[env_ids] = self.dynamic_goal_mask_table[rows, cols]
        self.dynamic_base_goals[env_ids] = self.terrain_goals[rows, cols]
        panel_dims = torch.tensor(
            self.cfg.dynamic_obstacles.panel_dims, device=self.device
        )
        self.dynamic_dims[env_ids] = panel_dims
        hurdle = self.dynamic_family[env_ids] == DYNAMIC_HURDLE
        self.dynamic_dims[env_ids[hurdle]] = panel_dims[[2, 1, 0]]

        difficulty = self.dynamic_difficulty[env_ids, None]
        dynamic_cfg = self.cfg.dynamic_obstacles

        def interpolate(values):
            return values[0] + (values[1] - values[0]) * difficulty

        max_amplitude = interpolate(dynamic_cfg.hurdle_amplitude)
        max_amplitude = torch.where(
            (self.dynamic_family[env_ids] == DYNAMIC_GAP)[:, None],
            interpolate(dynamic_cfg.gap_amplitude),
            max_amplitude,
        )
        max_amplitude = torch.where(
            (self.dynamic_family[env_ids] == DYNAMIC_TILTED_PADS)[:, None],
            interpolate(dynamic_cfg.tilted_pad_amplitude),
            max_amplitude,
        )
        max_amplitude = torch.where(
            (self.dynamic_family[env_ids] == DYNAMIC_STEP)[:, None],
            interpolate(dynamic_cfg.step_amplitude),
            max_amplitude,
        )
        self.dynamic_amplitude[env_ids] = max_amplitude * (
            0.5
            + 0.5
            * torch.rand(len(env_ids), self.num_dynamic_obstacles, device=self.device)
        )
        period_min = interpolate(dynamic_cfg.period_min)
        period_max = interpolate(dynamic_cfg.period_max)
        self.dynamic_period[env_ids] = period_min + (
            period_max - period_min
        ) * torch.rand(len(env_ids), self.num_dynamic_obstacles, device=self.device)
        self.dynamic_phase[env_ids] = (
            2
            * np.pi
            * torch.rand(len(env_ids), self.num_dynamic_obstacles, device=self.device)
        )
        self.dynamic_time[env_ids] = 0.0
        self._apply_dynamic_poses(env_ids)

    def _pre_physics_step(self):
        self.dynamic_time += self.sim_params.dt
        self._apply_dynamic_poses(
            torch.arange(self.num_envs, device=self.device, dtype=torch.long)
        )

    def _apply_dynamic_poses(self, env_ids):
        if len(env_ids) == 0:
            return
        phase = (
            2 * np.pi * self.dynamic_time[env_ids, None] / self.dynamic_period[env_ids]
            + self.dynamic_phase[env_ids]
        )
        offsets = self.dynamic_amplitude[env_ids] * torch.sin(phase)
        velocities = (
            self.dynamic_amplitude[env_ids]
            * (2 * np.pi / self.dynamic_period[env_ids])
            * torch.cos(phase)
        )
        self.dynamic_offset[env_ids] = offsets
        self.dynamic_velocity[env_ids] = velocities

        states = self.obstacle_root_states[env_ids].clone()
        specs = self.dynamic_specs[env_ids]
        states[..., :3] = specs[..., :3]
        states[..., 3:7] = 0.0
        states[..., 6] = 1.0
        states[..., 7:13] = 0.0

        hurdle = self.dynamic_family[env_ids] == DYNAMIC_HURDLE
        gap = self.dynamic_family[env_ids] == DYNAMIC_GAP
        tilted = self.dynamic_family[env_ids] == DYNAMIC_TILTED_PADS
        step = self.dynamic_family[env_ids] == DYNAMIC_STEP

        if torch.any(hurdle):
            height = self.cfg.dynamic_obstacles.panel_dims[0]
            states[hurdle, :, 0, 2] = (
                specs[hurdle, :, 0, 2] + specs[hurdle, :, 0, 5] / 2 - height / 2
            )
            zero = torch.zeros_like(offsets[hurdle])
            pitch = torch.full_like(zero, np.pi / 2)
            states[hurdle, :, 0, 3:7] = quat_from_euler_xyz(
                zero.flatten(), pitch.flatten(), zero.flatten()
            ).view(-1, self.num_dynamic_obstacles, 4)
            states[hurdle, :, 0, 0] += offsets[hurdle]
            states[hurdle, :, 0, 7] = velocities[hurdle]
        if torch.any(gap):
            states[gap, :, :, 0] += offsets[gap, :, None]
            states[gap, :, :, 7] = velocities[gap, :, None]
        if torch.any(tilted):
            roll = offsets[tilted]
            zero = torch.zeros_like(roll)
            states[tilted, :, 0, 3:7] = quat_from_euler_xyz(
                roll.flatten(), zero.flatten(), zero.flatten()
            ).view(-1, self.num_dynamic_obstacles, 4)
            states[tilted, :, 0, 10] = velocities[tilted]
        if torch.any(step):
            states[step, :, 0, 2] += offsets[step]
            states[step, :, 0, 9] = velocities[step]

        inactive = specs[..., 2] <= self.cfg.dynamic_obstacles.inactive_z / 2
        parking = torch.arange(
            self.num_dynamic_obstacles * self.num_dynamic_slots,
            device=self.device,
            dtype=torch.float,
        ).view(1, self.num_dynamic_obstacles, self.num_dynamic_slots)
        states[..., 0] = torch.where(
            inactive, self.env_origins[env_ids, None, None, 0] + parking, states[..., 0]
        )
        states[..., 1] = torch.where(
            inactive, self.env_origins[env_ids, None, None, 1] - 4.0, states[..., 1]
        )
        states[..., 2] = torch.where(
            inactive,
            self.cfg.dynamic_obstacles.inactive_z - parking,
            states[..., 2],
        )

        self.obstacle_root_states[env_ids] = states
        indices = self.dynamic_actor_indices[env_ids].flatten()
        self.gym.set_actor_root_state_tensor_indexed(
            self.sim,
            gymtorch.unwrap_tensor(self.all_root_states.view(-1, 13)),
            gymtorch.unwrap_tensor(indices),
            len(indices),
        )
        self._update_dynamic_goals(env_ids)

    def _update_dynamic_goals(self, env_ids):
        goals = self.dynamic_base_goals[env_ids].clone()
        gap = self.dynamic_family[env_ids] == DYNAMIC_GAP
        if torch.any(gap):
            goals[gap, 1 : self.num_dynamic_obstacles + 1, 0] += self.dynamic_offset[
                env_ids[gap]
            ]
        last_goal = goals[:, -1:].repeat(1, self.cfg.env.num_future_goal_obs, 1)
        self.env_goals[env_ids] = torch.cat((goals, last_goal), dim=1)
        self.cur_goals = self._gather_cur_goals()
        self.next_goals = self._gather_cur_goals(future=1)

    def _get_heights(self, env_ids=None):
        ids = (
            torch.arange(self.num_envs, device=self.device, dtype=torch.long)
            if env_ids is None
            else env_ids
        )
        points = quat_apply_yaw(
            self.base_quat[ids].repeat(1, self.num_height_points),
            self.height_points[ids],
        ) + self.root_states[ids, :3].unsqueeze(1)
        map_points = points + self.terrain.cfg.border_size
        map_points = (map_points / self.terrain.cfg.horizontal_scale).long()
        px = torch.clip(map_points[:, :, 0], 0, self.height_samples.shape[0] - 2)
        py = torch.clip(map_points[:, :, 1], 0, self.height_samples.shape[1] - 2)
        heights = torch.minimum(
            self.height_samples[px, py], self.height_samples[px + 1, py]
        )
        heights = torch.minimum(heights, self.height_samples[px, py + 1])
        heights = heights * self.terrain.cfg.vertical_scale

        states = self.obstacle_root_states[ids].reshape(len(ids), -1, 13)
        specs = self.dynamic_specs[ids].reshape(len(ids), -1, 7)
        dims = self.dynamic_dims[ids]
        for slot in range(self.num_dynamic_obstacles * self.num_dynamic_slots):
            center = states[:, slot, :3]
            in_x = (
                torch.abs(points[:, :, 0] - center[:, None, 0]) <= dims[:, None, 0] / 2
            )
            in_y = (
                torch.abs(points[:, :, 1] - center[:, None, 1]) <= dims[:, None, 1] / 2
            )
            active = specs[:, slot, 2] > self.cfg.dynamic_obstacles.inactive_z / 2
            top = (
                (center[:, None, 2] + dims[:, None, 2] / 2)
                .expand(-1, points.shape[1])
                .clone()
            )
            tilted = self.dynamic_family[ids] == DYNAMIC_TILTED_PADS
            if slot % self.num_dynamic_slots == 0 and torch.any(tilted):
                roll = self.dynamic_offset[ids[tilted], slot // self.num_dynamic_slots]
                top[tilted] = (
                    center[tilted, None, 2]
                    + dims[tilted, None, 2] / 2 * torch.cos(roll[:, None])
                    + (points[tilted, :, 1] - center[tilted, None, 1])
                    * torch.sin(roll[:, None])
                )
            cover = in_x & in_y & active[:, None]
            heights = torch.where(cover & (top > heights), top, heights)
        return heights

    def _reward_bad_dynamic_takeoff(self):
        # TODO: implement this penalty
        return torch.zeros(self.num_envs, dtype=torch.float, device=self.device)
