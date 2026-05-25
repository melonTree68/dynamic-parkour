"""Tiny dynamic-terrain viewer/debug entrypoint.

This script creates one environment with a selected dynamic obstacle and steps
zero actions. It intentionally does not create a PPO runner, load policies, log
to wandb, train, or evaluate.
"""

import isaacgym  # noqa: F401

from legged_gym.envs import *  # noqa: F401,F403
from legged_gym.utils.dynamic_terrain_suites import DYNAMIC_TERRAIN_SUITES
from legged_gym.utils import task_registry
from legged_gym.utils.helpers import parse_arguments

import torch


SUPPORTED_OBSTACLE_TYPES = (
    "moving_hurdle",
    "shifting_gap",
    "changing_step_height",
    "time_varying_ramp",
)
SUPPORTED_SUITES = tuple(DYNAMIC_TERRAIN_SUITES.keys())


def get_args():
    custom_parameters = [
        {"name": "--task", "type": str, "default": "a1", "help": "Task name."},
        {
            "name": "--obstacle_type",
            "type": str,
            "default": "moving_hurdle",
            "help": "Primitive dynamic obstacle type to inspect.",
        },
        {
            "name": "--suite",
            "type": str,
            "default": None,
            "help": "Dynamic terrain suite to inspect.",
        },
        {
            "name": "--layout_id",
            "type": int,
            "default": 0,
            "help": "Suite layout id when --suite is set.",
        },
        {
            "name": "--random_layout",
            "action": "store_true",
            "help": "Sample a layout per env from the selected suite.",
        },
        {
            "name": "--list_suites",
            "action": "store_true",
            "help": "Print available suites and layouts, then exit.",
        },
        {
            "name": "--print_state_every",
            "type": int,
            "default": 0,
            "help": "Print dynamic obstacle state every N steps.",
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
        {"name": "--rows", "type": int, "default": 2, "help": "Terrain rows."},
        {"name": "--cols", "type": int, "default": 2, "help": "Terrain cols."},
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


def list_suites():
    for suite_name, layouts in DYNAMIC_TERRAIN_SUITES.items():
        print("{}: {} layouts".format(suite_name, len(layouts)))
        for layout_id, layout in enumerate(layouts):
            print("  {}: {}".format(layout_id, layout["name"]))


def configure_tiny_dynamic_env(env_cfg, obstacle_type, suite, layout_id, random_layout, rows, cols):
    if suite is not None and suite not in SUPPORTED_SUITES:
        raise ValueError(
            "Unknown suite '{}'. Supported suites are {}.".format(
                suite, SUPPORTED_SUITES
            )
        )
    if suite is None and obstacle_type not in SUPPORTED_OBSTACLE_TYPES:
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

    env_cfg.domain_rand.randomize_friction = True
    env_cfg.domain_rand.push_robots = False
    env_cfg.domain_rand.randomize_base_mass = False
    env_cfg.domain_rand.randomize_base_com = False

    env_cfg.dynamic_obstacles.enable = True
    if suite is None:
        env_cfg.dynamic_obstacles.use_suites = False
        env_cfg.dynamic_obstacles.type = obstacle_type
    else:
        env_cfg.dynamic_obstacles.use_suites = True
        env_cfg.dynamic_obstacles.suite = suite
        env_cfg.dynamic_obstacles.layout_id = layout_id
        env_cfg.dynamic_obstacles.layout_randomization = random_layout
    return env_cfg


def summarize_state(state):
    summary = {
        "suite": state.get("suite"),
        "layout_id": state.get("layout_id"),
        "actor_types": state.get("actor_types"),
    }
    if "current_position" in state:
        summary["current_position"] = state["current_position"].detach().cpu().tolist()
    if "current_ramp_angle" in state:
        summary["current_ramp_angle"] = state["current_ramp_angle"].detach().cpu().tolist()
    return summary


def main():
    args = get_args()
    if args.list_suites:
        list_suites()
        return

    env_cfg, _ = task_registry.get_cfgs(name=args.task)
    env_cfg = configure_tiny_dynamic_env(
        env_cfg,
        args.obstacle_type,
        args.suite,
        args.layout_id,
        args.random_layout,
        max(2, args.rows),
        max(2, args.cols),
    )

    env, _ = task_registry.make_env(name=args.task, args=args, env_cfg=env_cfg)
    actions = torch.zeros(
        env.num_envs,
        env.num_actions,
        device=env.device,
        requires_grad=False,
    )

    if args.suite is None:
        target = "primitive '{}'".format(args.obstacle_type)
    else:
        target = "suite '{}' layout_id {} random_layout={}".format(
            args.suite, args.layout_id, args.random_layout
        )
    print("Viewing dynamic terrain {} for {} zero-action steps.".format(target, args.steps))

    for step_id in range(max(0, args.steps)):
        env.step(actions)
        if (
            args.print_state_every > 0
            and env.dynamic_obstacles is not None
            and step_id % args.print_state_every == 0
        ):
            print(
                "step {} dynamic state: {}".format(
                    step_id, summarize_state(env.dynamic_obstacles.get_state())
                )
            )

    if env.dynamic_obstacles is not None:
        state = env.dynamic_obstacles.get_state()
        print("Final dynamic obstacle state keys:", sorted(state.keys()))


if __name__ == "__main__":
    main()
