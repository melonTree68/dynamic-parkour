# SPDX-FileCopyrightText: Copyright (c) 2021 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Copyright (c) 2021 ETH Zurich, Nikita Rudin

from legged_gym import LEGGED_GYM_ROOT_DIR
import os
import code

import isaacgym
from legged_gym.envs import *
from legged_gym.utils import get_args, export_policy_as_jit, task_registry, Logger
from isaacgym import gymtorch, gymapi, gymutil
import numpy as np
import torch
import cv2
from collections import deque
import statistics
import faulthandler
from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import datetime
from time import time, sleep
from legged_gym.utils import webviewer


def get_load_path(root, load_run=-1, checkpoint=-1, model_name_include="model"):
    if checkpoint == -1:
        models = [file for file in os.listdir(root) if model_name_include in file]
        models.sort(key=lambda m: "{0:0>15}".format(m))
        model = models[-1]
        checkpoint = model.split("_")[-1].split(".")[0]
    return model, checkpoint


def _parse_vec3_arg(value, name):
    try:
        values = [float(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise ValueError(f"{name} must be three comma-separated numbers.") from exc
    if len(values) != 3:
        raise ValueError(f"{name} must be three comma-separated numbers.")
    return np.array(values, dtype=np.float32)


def _rotate_yaw(local_vec, yaw):
    cos_yaw = np.cos(yaw)
    sin_yaw = np.sin(yaw)
    return np.array(
        [
            cos_yaw * local_vec[0] - sin_yaw * local_vec[1],
            sin_yaw * local_vec[0] + cos_yaw * local_vec[1],
            local_vec[2],
        ],
        dtype=np.float32,
    )


def _yaw_from_quat(quat):
    x = quat[:, 0]
    y = quat[:, 1]
    z = quat[:, 2]
    w = quat[:, 3]
    return torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def _validate_video_args(args):
    if args.video_episodes <= 0:
        raise ValueError("--video_episodes must be positive.")
    if args.video_episode_timeout_s <= 0:
        raise ValueError("--video_episode_timeout_s must be positive.")
    if args.video_width <= 0 or args.video_height <= 0:
        raise ValueError("--video_width and --video_height must be positive.")
    if args.video_fps <= 0:
        raise ValueError("--video_fps must be positive.")
    args.video_camera_mode = args.video_camera_mode.lower()
    if args.video_camera_mode not in ("yaw", "attached"):
        raise ValueError("--video_camera_mode must be either 'yaw' or 'attached'.")
    args.video_camera_pos = _parse_vec3_arg(args.video_camera_pos, "--video_camera_pos")
    args.video_camera_target = _parse_vec3_arg(
        args.video_camera_target, "--video_camera_target"
    )
    if args.headless:
        raise ValueError("--record_video requires graphics; do not pass --headless.")


class PlayVideoRecorder:
    def __init__(self, env, args):
        self.env = env
        self.args = args
        self.num_episodes = args.video_episodes
        self.width = args.video_width
        self.height = args.video_height
        self.camera_pos = args.video_camera_pos
        self.camera_target = args.video_camera_target
        self.camera_mode = args.video_camera_mode
        self.completed_episodes = np.zeros(env.num_envs, dtype=np.int32)
        self.max_steps = self.num_episodes * (int(env.max_episode_length) + 1) + 1
        self.camera_handles = []
        self.writers = []
        self.last_reported_complete = 0

        repo_root = os.path.dirname(LEGGED_GYM_ROOT_DIR)
        exptid = args.exptid or "default"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(
            repo_root, "videos", args.proj_name, exptid, timestamp
        )
        os.makedirs(self.output_dir, exist_ok=True)

        self._create_cameras()
        self._open_writers()
        print(
            "Recording videos to",
            self.output_dir,
            "envs",
            env.num_envs,
            "episodes",
            self.num_episodes,
            "timeout_s",
            args.video_episode_timeout_s,
        )

    @property
    def done(self):
        return bool(np.all(self.completed_episodes >= self.num_episodes))

    def _create_cameras(self):
        camera_props = gymapi.CameraProperties()
        camera_props.width = self.width
        camera_props.height = self.height
        camera_props.enable_tensors = False

        for i in range(self.env.num_envs):
            camera_handle = self.env.gym.create_camera_sensor(
                self.env.envs[i], camera_props
            )
            self.camera_handles.append(camera_handle)

            if self.camera_mode == "attached":
                local_transform = gymapi.Transform()
                local_transform.p = gymapi.Vec3(*self.camera_pos)
                local_transform.r = gymapi.Quat.from_euler_zyx(
                    0,
                    np.radians(self.args.video_camera_pitch_deg),
                    0,
                )
                root_handle = self.env.gym.get_actor_root_rigid_body_handle(
                    self.env.envs[i], self.env.actor_handles[i]
                )
                self.env.gym.attach_camera_to_body(
                    camera_handle,
                    self.env.envs[i],
                    root_handle,
                    local_transform,
                    gymapi.FOLLOW_TRANSFORM,
                )

    def _open_writers(self):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        for i in range(self.env.num_envs):
            path = os.path.join(self.output_dir, f"env_{i:03d}.mp4")
            writer = cv2.VideoWriter(
                path, fourcc, self.args.video_fps, (self.width, self.height)
            )
            if not writer.isOpened():
                self.release()
                raise RuntimeError(f"Failed to open video writer: {path}")
            self.writers.append(writer)

    def _update_yaw_cameras(self, active_ids):
        root_states = self.env.root_states.detach()
        root_pos = root_states[:, :3].cpu().numpy()
        yaw = _yaw_from_quat(root_states[:, 3:7]).cpu().numpy()

        for env_id in active_ids:
            cam_pos = root_pos[env_id] + _rotate_yaw(self.camera_pos, yaw[env_id])
            cam_target = root_pos[env_id] + _rotate_yaw(self.camera_target, yaw[env_id])
            self.env.gym.set_camera_location(
                self.camera_handles[env_id],
                self.env.envs[env_id],
                gymapi.Vec3(*cam_pos),
                gymapi.Vec3(*cam_target),
            )

    def capture(self):
        active_ids = np.flatnonzero(self.completed_episodes < self.num_episodes)
        if len(active_ids) == 0:
            return

        if self.camera_mode == "yaw":
            self._update_yaw_cameras(active_ids)

        self.env.gym.step_graphics(self.env.sim)
        self.env.gym.render_all_camera_sensors(self.env.sim)

        for env_id in active_ids:
            image = self.env.gym.get_camera_image(
                self.env.sim,
                self.env.envs[env_id],
                self.camera_handles[env_id],
                gymapi.IMAGE_COLOR,
            )
            rgba = np.asarray(image, dtype=np.uint8).reshape(self.height, self.width, 4)
            bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
            self.writers[env_id].write(bgr)

    def update_done(self, dones):
        dones_np = dones.detach().cpu().numpy().astype(bool)
        active_done = np.logical_and(
            dones_np, self.completed_episodes < self.num_episodes
        )
        self.completed_episodes[active_done] += 1

        complete = int(np.sum(self.completed_episodes >= self.num_episodes))
        if complete != self.last_reported_complete:
            print(f"Video progress: {complete}/{self.env.num_envs} env videos done")
            self.last_reported_complete = complete

    def warn_if_incomplete(self):
        if self.done:
            return
        complete = int(np.sum(self.completed_episodes >= self.num_episodes))
        print(f"Video recording stopped early: {complete}/{self.env.num_envs} complete")

    def release(self):
        for writer in self.writers:
            writer.release()
        self.writers = []


def play(args):
    if args.web:
        web_viewer = webviewer.WebViewer()
    faulthandler.enable()
    exptid = args.exptid
    log_pth = "../../logs/{}/".format(args.proj_name) + args.exptid

    env_cfg, train_cfg = task_registry.get_cfgs(name=args.task)
    # override some parameters for testing
    if args.nodelay:
        env_cfg.domain_rand.action_delay_view = 0
    env_cfg.env.num_envs = 16 if not args.save else 64
    env_cfg.env.episode_length_s = 60
    if args.record_video:
        _validate_video_args(args)
        env_cfg.env.episode_length_s = args.video_episode_timeout_s
    env_cfg.commands.resampling_time = 60
    env_cfg.terrain.num_rows = 5
    env_cfg.terrain.num_cols = 5
    env_cfg.terrain.height = [0.02, 0.02]
    if args.task == "a1":
        env_cfg.terrain.terrain_dict = {
            **{name: 0.0 for name in env_cfg.terrain.terrain_dict},
            "parkour": 0.2,
            "parkour_hurdle": 0.2,
            "parkour_step": 0.2,
            "parkour_gap": 0.2,
            "demo": 0.2,
        }
    elif args.task == "a1_dynamic":
        env_cfg.terrain.terrain_dict = {
            **{name: 0.0 for name in env_cfg.terrain.terrain_dict},
            "dynamic_hurdle": 0.2,
            "dynamic_gap": 0.2,
            "dynamic_tilted_pads": 0.2,
            "dynamic_step": 0.2,
            "dynamic_demo": 0.2,
        }
    elif args.task == "a1_mixed":
        env_cfg.terrain.terrain_dict = {
            **{name: 0.0 for name in env_cfg.terrain.terrain_dict},
            "dynamic_hurdle": 0.2,
            "dynamic_gap": 0.2,
            "mixed_tilted_pads": 0.2,
            "parkour_step": 0.2,
            "mixed_demo": 0.2,
        }
    else:
        raise ValueError(f"Unknown task: {args.task}")

    env_cfg.terrain.terrain_proportions = list(env_cfg.terrain.terrain_dict.values())
    env_cfg.terrain.curriculum = False
    env_cfg.terrain.max_difficulty = True

    env_cfg.depth.angle = [0, 1]
    env_cfg.noise.add_noise = True
    env_cfg.domain_rand.randomize_friction = True
    env_cfg.domain_rand.push_robots = False
    env_cfg.domain_rand.push_interval_s = 6
    env_cfg.domain_rand.randomize_base_mass = False
    env_cfg.domain_rand.randomize_base_com = False

    depth_latent_buffer = []
    # prepare environment
    env: LeggedRobot
    env, _ = task_registry.make_env(name=args.task, args=args, env_cfg=env_cfg)
    obs = env.get_observations()

    if args.web:
        web_viewer.setup(env)

    # load policy
    train_cfg.runner.resume = True
    ppo_runner, train_cfg, log_pth = task_registry.make_alg_runner(
        log_root=log_pth,
        env=env,
        name=args.task,
        args=args,
        train_cfg=train_cfg,
        return_log_dir=True,
    )

    if args.use_jit:
        path = os.path.join(log_pth, "traced")
        model, checkpoint = get_load_path(root=path, checkpoint=args.checkpoint)
        path = os.path.join(path, model)
        print("Loading jit for policy: ", path)
        policy_jit = torch.jit.load(path, map_location=env.device)
    else:
        policy = ppo_runner.get_inference_policy(device=env.device)
    estimator = ppo_runner.get_estimator_inference_policy(device=env.device)
    if env.cfg.depth.use_camera:
        depth_encoder = ppo_runner.get_depth_encoder_inference_policy(device=env.device)

    video_recorder = PlayVideoRecorder(env, args) if args.record_video else None

    actions = torch.zeros(env.num_envs, 12, device=env.device, requires_grad=False)
    infos = {}
    infos["depth"] = (
        env.depth_buffer.clone().to(ppo_runner.device)[:, -1]
        if ppo_runner.if_depth
        else None
    )

    try:
        max_steps = (
            video_recorder.max_steps
            if video_recorder is not None
            else 10 * int(env.max_episode_length)
        )
        for i in range(max_steps):
            if video_recorder is not None:
                if video_recorder.done:
                    break
                video_recorder.capture()

            if args.use_jit:
                if env.cfg.depth.use_camera:
                    if infos["depth"] is not None:
                        depth_latent = torch.ones(
                            (env_cfg.env.num_envs, 32), device=env.device
                        )
                        actions, depth_latent = policy_jit(
                            obs.detach(), True, infos["depth"], depth_latent
                        )
                    else:
                        depth_buffer = torch.ones(
                            (env_cfg.env.num_envs, 58, 87), device=env.device
                        )
                        actions, depth_latent = policy_jit(
                            obs.detach(), False, depth_buffer, depth_latent
                        )
                else:
                    obs_jit = torch.cat(
                        (
                            obs.detach()[
                                :, : env_cfg.env.n_proprio + env_cfg.env.n_priv
                            ],
                            obs.detach()[
                                :,
                                -env_cfg.env.history_len * env_cfg.env.n_proprio :,
                            ],
                        ),
                        dim=1,
                    )
                    actions = policy(obs_jit)
            else:
                if env.cfg.depth.use_camera:
                    if infos["depth"] is not None:
                        obs_student = obs[:, : env.cfg.env.n_proprio].clone()
                        obs_student[:, 6:8] = 0
                        depth_latent_and_yaw = depth_encoder(
                            infos["depth"], obs_student
                        )
                        scan_latent_dim = train_cfg.policy.scan_encoder_dims[-1]
                        dynamic_latent_dim = getattr(
                            env.cfg.env, "n_dynamic_env_latent", 0
                        )
                        depth_latent = depth_latent_and_yaw[:, :scan_latent_dim]
                        dynamic_env_latent = depth_latent_and_yaw[
                            :, scan_latent_dim : scan_latent_dim + dynamic_latent_dim
                        ]
                        yaw = depth_latent_and_yaw[:, -2:]
                    obs[:, 6:8] = 1.5 * yaw

                else:
                    depth_latent = None
                    dynamic_env_latent = None

                if hasattr(ppo_runner.alg, "depth_actor"):
                    actions = ppo_runner.alg.depth_actor(
                        obs.detach(),
                        hist_encoding=True,
                        scandots_latent=depth_latent,
                        dynamic_env_latent=dynamic_env_latent,
                    )
                else:
                    actions = policy(
                        obs.detach(),
                        hist_encoding=True,
                        scandots_latent=depth_latent,
                        dynamic_env_latent=dynamic_env_latent,
                    )

            obs, _, rews, dones, infos = env.step(actions.detach())
            if args.web:
                web_viewer.render(
                    fetch_results=True,
                    step_graphics=True,
                    render_all_camera_sensors=True,
                    wait_for_page_load=True,
                )

            if video_recorder is not None:
                video_recorder.update_done(dones)

            if video_recorder is None or i % max(args.video_fps, 1) == 0:
                print(
                    "time:",
                    env.episode_length_buf[env.lookat_id].item() / 50,
                    "cmd vx",
                    env.commands[env.lookat_id, 0].item(),
                    "actual vx",
                    env.base_lin_vel[env.lookat_id, 0].item(),
                )

            id = env.lookat_id

        if video_recorder is not None:
            video_recorder.warn_if_incomplete()
    finally:
        if video_recorder is not None:
            video_recorder.release()


if __name__ == "__main__":
    EXPORT_POLICY = False
    RECORD_FRAMES = False
    MOVE_CAMERA = False
    args = get_args()
    play(args)
