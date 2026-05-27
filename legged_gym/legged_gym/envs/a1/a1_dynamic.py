import numpy as np
import torch

from isaacgym import gymapi, gymtorch
from isaacgym.torch_utils import quat_from_euler_xyz

from legged_gym.envs.base.legged_robot import LeggedRobot
from legged_gym.utils.math import quat_apply_yaw
from legged_gym.utils.terrain import (
    DYNAMIC_GAP,
    DYNAMIC_HURDLE,
    DYNAMIC_NONE,
    DYNAMIC_STEP,
    DYNAMIC_TILTED_PADS,
)


class DynamicLeggedRobot(LeggedRobot):
    """A1 parkour environment with scripted physical obstacle actors."""

    def __init__(self, cfg, sim_params, physics_engine, sim_device, headless):
        cfg.terrain.dynamic_obstacles = cfg.dynamic_obstacles
        self.num_dynamic_obstacles = cfg.dynamic_obstacles.num_obstacles
        self.num_dynamic_slots = cfg.dynamic_obstacles.slots_per_obstacle
        self.num_actors_per_env = (
            1 + self.num_dynamic_obstacles * self.num_dynamic_slots
        )
        super().__init__(cfg, sim_params, physics_engine, sim_device, headless)

    def _hurdle_body_height(self):
        return self.cfg.dynamic_obstacles.hurdle_height_max[1] + 0.05

    def _step_body_height(self):
        cfg = self.cfg.dynamic_obstacles
        return 3 * cfg.step_height_max[1] + cfg.step_amplitude[1] + 0.05

    def _prepare_additional_assets(self):
        options = gymapi.AssetOptions()
        options.disable_gravity = True
        cfg = self.cfg.dynamic_obstacles
        step_len, step_width = cfg.step_dims
        self.dynamic_assets = {
            DYNAMIC_NONE: self.gym.create_box(
                self.sim, *cfg.tilted_pad_dims, options
            ),
            DYNAMIC_HURDLE: self.gym.create_box(
                self.sim,
                cfg.hurdle_thickness,
                cfg.hurdle_width,
                self._hurdle_body_height(),
                options,
            ),
            DYNAMIC_GAP: self.gym.create_box(
                self.sim, *cfg.gap_platform_dims, options
            ),
            DYNAMIC_TILTED_PADS: self.gym.create_box(
                self.sim, *cfg.tilted_pad_dims, options
            ),
            DYNAMIC_STEP: self.gym.create_box(
                self.sim, step_len, step_width, self._step_body_height(), options
            ),
        }
        self.dynamic_actor_handles = []

    def _create_additional_actors(self, env_handle, env_id):
        row = int(self.terrain_levels[env_id].item())
        col = int(self.terrain_types[env_id].item())
        specs = self.terrain.dynamic_obstacle_specs[row, col].reshape(-1, 7)
        motion_types = self.terrain.dynamic_motion_types[row, col].reshape(-1)
        handles = []
        for i, motion_type in enumerate(motion_types):
            pose = gymapi.Transform()
            x, y, z = specs[i, :3]
            if motion_type == DYNAMIC_NONE:
                x = float(self.env_origins[env_id, 0].item()) + i
                y = float(self.env_origins[env_id, 1].item()) - 4.0
                z = self.cfg.dynamic_obstacles.inactive_z - i
            pose.p = gymapi.Vec3(float(x), float(y), float(z))
            handle = self.gym.create_actor(
                env_handle,
                self.dynamic_assets[int(motion_type)],
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
        self.dynamic_motion_types_table = torch.from_numpy(
            self.terrain.dynamic_motion_types
        ).to(device=self.device, dtype=torch.long)
        self.dynamic_motion_groups_table = torch.from_numpy(
            self.terrain.dynamic_motion_groups
        ).to(device=self.device, dtype=torch.long)
        self.dynamic_goal_groups_table = torch.from_numpy(
            self.terrain.dynamic_goal_groups
        ).to(device=self.device, dtype=torch.long)

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
        self.dynamic_motion_types = torch.zeros(
            self.num_envs,
            self.num_dynamic_obstacles,
            self.num_dynamic_slots,
            device=self.device,
            dtype=torch.long,
        )
        self.dynamic_motion_groups = torch.full_like(self.dynamic_motion_types, -1)
        self.dynamic_goal_groups = torch.full(
            (self.num_envs, self.cfg.terrain.num_goals),
            -1,
            device=self.device,
            dtype=torch.long,
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
        self.dynamic_dims = torch.zeros(
            self.num_envs,
            self.num_dynamic_obstacles,
            self.num_dynamic_slots,
            3,
            device=self.device,
        )

        self.dynamic_actor_indices = (
            torch.arange(self.num_envs, dtype=torch.int32, device=self.device)[:, None]
            * self.num_actors_per_env
            + torch.arange(
                1, self.num_actors_per_env, dtype=torch.int32, device=self.device
            )[None, :]
        )

    def _reset_additional_actors(self, env_ids):
        rows = self.terrain_levels[env_ids]
        cols = self.terrain_types[env_ids]
        self.dynamic_family[env_ids] = self.dynamic_family_table[rows, cols]
        self.dynamic_difficulty[env_ids] = self.dynamic_difficulty_table[rows, cols]
        self.dynamic_specs[env_ids] = self.dynamic_specs_table[rows, cols]
        self.dynamic_motion_types[env_ids] = self.dynamic_motion_types_table[rows, cols]
        self.dynamic_motion_groups[env_ids] = self.dynamic_motion_groups_table[rows, cols]
        self.dynamic_goal_groups[env_ids] = self.dynamic_goal_groups_table[rows, cols]
        self.dynamic_base_goals[env_ids] = self.terrain_goals[rows, cols]
        self.dynamic_dims[env_ids] = self.dynamic_specs[env_ids, ..., 3:6]

        difficulty = self.dynamic_difficulty[env_ids, None]
        dynamic_cfg = self.cfg.dynamic_obstacles
        group_types = self.dynamic_motion_types[env_ids].amax(dim=-1)

        def interpolate(values):
            return values[0] + (values[1] - values[0]) * difficulty

        max_amplitude = torch.zeros_like(self.dynamic_amplitude[env_ids])
        period_min = torch.ones_like(max_amplitude)
        period_max = torch.ones_like(max_amplitude)
        settings = (
            (DYNAMIC_HURDLE, dynamic_cfg.hurdle_amplitude,
             dynamic_cfg.hurdle_period_min, dynamic_cfg.hurdle_period_max),
            (DYNAMIC_GAP, dynamic_cfg.gap_amplitude,
             dynamic_cfg.gap_period_min, dynamic_cfg.gap_period_max),
            (DYNAMIC_TILTED_PADS, dynamic_cfg.tilted_pad_amplitude,
             dynamic_cfg.tilted_pad_period_min, dynamic_cfg.tilted_pad_period_max),
            (DYNAMIC_STEP, dynamic_cfg.step_amplitude,
             dynamic_cfg.step_period_min, dynamic_cfg.step_period_max),
        )
        for motion_type, amplitude, minimum, maximum in settings:
            mask = group_types == motion_type
            max_amplitude = torch.where(mask, interpolate(amplitude), max_amplitude)
            period_min = torch.where(mask, interpolate(minimum), period_min)
            period_max = torch.where(mask, interpolate(maximum), period_max)

        min_fraction = dynamic_cfg.amplitude_min_fraction
        sampled_amplitude = max_amplitude * (
            min_fraction
            + (1.0 - min_fraction)
            * torch.rand(len(env_ids), self.num_dynamic_obstacles, device=self.device)
        )
        sampled_period = period_min + (period_max - period_min) * torch.rand(
            len(env_ids), self.num_dynamic_obstacles, device=self.device
        )
        sampled_phase = 2 * np.pi * torch.rand(
            len(env_ids), self.num_dynamic_obstacles, device=self.device
        )
        pure_gap = self.dynamic_family[env_ids] == DYNAMIC_GAP
        if torch.any(pure_gap):
            sampled_amplitude[pure_gap] = sampled_amplitude[pure_gap, :1]
            sampled_period[pure_gap] = sampled_period[pure_gap, :1]
            sampled_phase[pure_gap] = sampled_phase[pure_gap, :1]
        self.dynamic_amplitude[env_ids] = sampled_amplitude
        self.dynamic_period[env_ids] = sampled_period
        self.dynamic_phase[env_ids] = sampled_phase
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
        motion_types = self.dynamic_motion_types[env_ids]
        motion_groups = self.dynamic_motion_groups[env_ids]
        group_ids = torch.clamp(motion_groups, min=0)
        slot_offsets = torch.gather(offsets, 1, group_ids.view(len(env_ids), -1)).view_as(
            motion_groups
        )
        slot_velocities = torch.gather(
            velocities, 1, group_ids.view(len(env_ids), -1)
        ).view_as(motion_groups)
        active = motion_types != DYNAMIC_NONE
        slot_offsets = torch.where(active, slot_offsets, torch.zeros_like(slot_offsets))
        slot_velocities = torch.where(
            active, slot_velocities, torch.zeros_like(slot_velocities)
        )

        states[..., :3] = specs[..., :3]
        states[..., 3:7] = 0.0
        states[..., 6] = 1.0
        states[..., 7:13] = 0.0

        translate_x = (motion_types == DYNAMIC_HURDLE) | (motion_types == DYNAMIC_GAP)
        move_z = motion_types == DYNAMIC_STEP
        tilted = motion_types == DYNAMIC_TILTED_PADS
        states[..., 0] += torch.where(
            translate_x, slot_offsets, torch.zeros_like(slot_offsets)
        )
        states[..., 2] += torch.where(move_z, slot_offsets, torch.zeros_like(slot_offsets))
        states[..., 7] = torch.where(
            translate_x, slot_velocities, torch.zeros_like(slot_velocities)
        )
        states[..., 9] = torch.where(
            move_z, slot_velocities, torch.zeros_like(slot_velocities)
        )

        zero = torch.zeros_like(slot_offsets)
        tilted_quat = quat_from_euler_xyz(
            slot_offsets.flatten(), zero.flatten(), zero.flatten()
        ).view(len(env_ids), self.num_dynamic_obstacles, self.num_dynamic_slots, 4)
        states[..., 3:7] = torch.where(tilted[..., None], tilted_quat, states[..., 3:7])
        states[..., 10] = torch.where(
            tilted, slot_velocities, torch.zeros_like(slot_velocities)
        )

        parking = torch.arange(
            self.num_dynamic_obstacles * self.num_dynamic_slots,
            device=self.device,
            dtype=torch.float,
        ).view(1, self.num_dynamic_obstacles, self.num_dynamic_slots)
        states[..., 0] = torch.where(
            active, states[..., 0], self.env_origins[env_ids, None, None, 0] + parking
        )
        states[..., 1] = torch.where(
            active, states[..., 1], self.env_origins[env_ids, None, None, 1] - 4.0
        )
        states[..., 2] = torch.where(
            active, states[..., 2], self.cfg.dynamic_obstacles.inactive_z - parking
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
        groups = self.dynamic_goal_groups[env_ids]
        moving = groups >= 0
        offsets = torch.gather(
            self.dynamic_offset[env_ids], 1, torch.clamp(groups, min=0)
        )
        goals[..., 0] += torch.where(moving, offsets, torch.zeros_like(offsets))
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
        dims = self.dynamic_dims[ids].reshape(len(ids), -1, 3)
        motion_types = self.dynamic_motion_types[ids].reshape(len(ids), -1)
        motion_groups = self.dynamic_motion_groups[ids].reshape(len(ids), -1)
        roll = torch.gather(
            self.dynamic_offset[ids], 1, torch.clamp(motion_groups, min=0)
        )
        for slot in range(self.num_dynamic_obstacles * self.num_dynamic_slots):
            center = states[:, slot, :3]
            in_x = (
                torch.abs(points[:, :, 0] - center[:, None, 0])
                <= dims[:, slot, None, 0] / 2
            )
            in_y = (
                torch.abs(points[:, :, 1] - center[:, None, 1])
                <= dims[:, slot, None, 1] / 2
            )
            active = motion_types[:, slot] != DYNAMIC_NONE
            top = (
                center[:, None, 2] + dims[:, slot, None, 2] / 2
            ).expand(-1, points.shape[1]).clone()
            tilted = motion_types[:, slot] == DYNAMIC_TILTED_PADS
            if torch.any(tilted):
                slot_roll = roll[tilted, slot]
                top[tilted] = (
                    center[tilted, None, 2]
                    + dims[tilted, slot, None, 2] / 2 * torch.cos(slot_roll[:, None])
                    + (points[tilted, :, 1] - center[tilted, None, 1])
                    * torch.sin(slot_roll[:, None])
                )
            cover = in_x & in_y & active[:, None]
            heights = torch.where(cover & (top > heights), top, heights)
        return heights

    def _reward_bad_dynamic_takeoff(self):
        # TODO: implement this penalty
        return torch.zeros(self.num_envs, dtype=torch.float, device=self.device)
