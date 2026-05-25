"""Tiny dynamic-terrain viewer/debug entrypoint.

This script creates one environment with a selected dynamic obstacle and steps
zero actions. It intentionally does not create a PPO runner, load policies, log
to wandb, train, or evaluate.
"""

import isaacgym  # noqa: F401

from legged_gym.envs import *  # noqa: F401,F403
from legged_gym.utils import task_registry
from legged_gym.utils.helpers import parse_arguments

import torch


SUPPORTED_OBSTACLE_TYPES = (
    "moving_hurdle",
    "shifting_gap",
    "changing_step_height",
    "time_varying_ramp",
)


def get_args():
    custom_parameters = [
        {"name": "--task", "type": str, "default": "a1", "help": "Task name."},
        {
            "name": "--obstacle_type",
            "type": str,
            "default": "moving_hurdle",
            "help": "Dynamic obstacle type to inspect.",
        },
        {
            "name": "--steps",
            "type": int,
            "default": 1000,
            "help": "Number of zero-action simulation steps.",
        },
        {"name": "--headless", "action": "store_true", "help": "Run without viewer."},
        {
            "name": "--num_envs",
            "type": int,
            "default": 1,
            "help": "Kept for compatibility; forced to 1 by this script.",
        },
        {"name": "--rows", "type": int, "default": 1, "help": "Terrain rows."},
        {"name": "--cols", "type": int, "default": 1, "help": "Terrain cols."},
        {"name": "--seed", "type": int, "help": "Random seed."},
        {
            "name": "--device",
            "type": str,
            "default": "cuda:0",
            "help": "Device for sim, RL placeholder, and graphics.",
        },
        {
            "name": "--rl_device",
            "type": str,
            "default": "cuda:0",
            "help": "Unused by this script, required by shared argument helpers.",
        },
        {"name": "--use_camera", "action": "store_true", "help": "Leave disabled."},
        {"name": "--task_both", "action": "store_true", "help": "Compatibility flag."},
        {"name": "--delay", "action": "store_true", "help": "Compatibility flag."},
        {"name": "--resume", "action": "store_true", "help": "Compatibility flag."},
    ]
    args = parse_arguments(
        description="Dynamic terrain actor viewer",
        custom_parameters=custom_parameters,
    )
    args.sim_device_id = args.compute_device_id
    args.sim_device = args.sim_device_type
    if args.sim_device == "cuda":
        args.sim_device += ":{}".format(args.sim_device_id)
    args.num_envs = 1
    return args


def configure_tiny_dynamic_env(env_cfg, obstacle_type, rows, cols):
    if obstacle_type not in SUPPORTED_OBSTACLE_TYPES:
        raise ValueError(
            "Unknown obstacle_type '{}'. Supported types are {}.".format(
                obstacle_type, SUPPORTED_OBSTACLE_TYPES
            )
        )

    env_cfg.env.num_envs = 1
    env_cfg.env.episode_length_s = 20
    env_cfg.depth.use_camera = False
    env_cfg.noise.add_noise = False
    env_cfg.commands.resampling_time = 60

    env_cfg.terrain.num_rows = rows
    env_cfg.terrain.num_cols = cols
    env_cfg.terrain.curriculum = False
    env_cfg.terrain.max_init_terrain_level = 0
    if hasattr(env_cfg.terrain, "terrain_dict"):
        for terrain_name in env_cfg.terrain.terrain_dict:
            env_cfg.terrain.terrain_dict[terrain_name] = 0.0
        env_cfg.terrain.terrain_dict["parkour_flat"] = 1.0
        env_cfg.terrain.terrain_proportions = list(
            env_cfg.terrain.terrain_dict.values()
        )

    env_cfg.domain_rand.randomize_friction = False
    env_cfg.domain_rand.push_robots = False
    env_cfg.domain_rand.randomize_base_mass = False
    env_cfg.domain_rand.randomize_base_com = False

    env_cfg.dynamic_obstacles.enable = True
    env_cfg.dynamic_obstacles.type = obstacle_type
    return env_cfg


def main():
    args = get_args()
    env_cfg, _ = task_registry.get_cfgs(name=args.task)
    env_cfg = configure_tiny_dynamic_env(
        env_cfg,
        args.obstacle_type,
        max(1, args.rows),
        max(1, args.cols),
    )

    env, _ = task_registry.make_env(name=args.task, args=args, env_cfg=env_cfg)
    actions = torch.zeros(
        env.num_envs,
        env.num_actions,
        device=env.device,
        requires_grad=False,
    )

    print(
        "Viewing dynamic obstacle '{}' for {} zero-action steps.".format(
            args.obstacle_type, args.steps
        )
    )
    for _ in range(max(0, args.steps)):
        env.step(actions)

    if env.dynamic_obstacles is not None:
        state = env.dynamic_obstacles.get_state()
        print("Final dynamic obstacle state keys:", sorted(state.keys()))


if __name__ == "__main__":
    main()
