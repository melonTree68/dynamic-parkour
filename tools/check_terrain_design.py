"""Static checks for the dynamic terrain design scaffold.

The checks are intentionally text/AST based so they can run without launching
Isaac Gym simulation, PPO training, evaluation, or a viewer.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OBSTACLE_TYPES = (
    "moving_hurdle",
    "shifting_gap",
    "changing_step_height",
    "time_varying_ramp",
)


def read(relative_path):
    return (ROOT / relative_path).read_text()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_dynamic_obstacle_manager():
    source = read("legged_gym/legged_gym/utils/dynamic_obstacles.py")
    for obstacle_type in OBSTACLE_TYPES:
        require(obstacle_type in source, "{} missing from manager".format(obstacle_type))

    for helper in [
        "_create_moving_hurdle",
        "_create_shifting_gap",
        "_create_changing_step_height",
        "_create_time_varying_ramp",
        "_update_moving_hurdle",
        "_update_shifting_gap",
        "_update_changing_step_height",
        "_update_time_varying_ramp",
    ]:
        require(helper in source, "{} missing from manager".format(helper))

    require("raise ValueError" in source, "manager should reject unknown obstacle types")
    require("set_actor_root_state_tensor_indexed" in source, "actor root updates missing")
    require("heightfield" in source, "static mesh/heightfield intent should be documented")


def check_config_defaults():
    source = read("legged_gym/legged_gym/envs/base/legged_robot_config.py")
    dynamic_block_start = source.index("class dynamic_obstacles:")
    dynamic_block = source[dynamic_block_start:]
    require("enable = False" in dynamic_block, "dynamic obstacles must stay disabled")
    require('type = "moving_hurdle"' in dynamic_block, "default obstacle type changed")
    for field in [
        "gap_edge_length",
        "gap_motion_axis",
        "gap_amplitude_range",
        "step_height_amplitude_range",
        "ramp_base_pitch",
        "ramp_pitch_amplitude_range",
    ]:
        require(field in dynamic_block, "{} missing from config".format(field))


def check_legged_robot_gating():
    source = read("legged_gym/legged_gym/envs/base/legged_robot.py")
    require(
        "if self.cfg.dynamic_obstacles.enable:" in source,
        "LeggedRobot should create manager only when enabled",
    )
    for call in [
        "self.dynamic_obstacles.create_assets()",
        "self.dynamic_obstacles.create_obstacles_for_env",
        "self.dynamic_obstacles.bind_root_state_tensor",
        "self.dynamic_obstacles.reset",
        "self.dynamic_obstacles.update",
    ]:
        require(call in source, "{} missing from LeggedRobot".format(call))


def check_viewer_script():
    source = read("legged_gym/legged_gym/scripts/view_dynamic_terrain.py")
    require("task_registry.make_env" in source, "viewer should create env via registry")
    require(
        "make_alg_runner" not in source,
        "viewer must not create PPO runner",
    )
    require("import wandb" not in source, "viewer must not import wandb")
    require("wandb.init" not in source, "viewer must not create wandb runs")
    require("env_cfg.env.num_envs = 1" in source, "viewer must force one env")
    for obstacle_type in OBSTACLE_TYPES:
        require(obstacle_type in source, "{} missing from viewer".format(obstacle_type))
    require(
        source.index("import isaacgym") < source.index("import torch"),
        "viewer must import isaacgym before torch",
    )


def check_docs():
    for relative_path in [
        "docs/DYNAMIC_TERRAIN_DESIGN.md",
        "docs/DYNAMIC_TERRAIN_USAGE.md",
        "docs/DYNAMIC_TERRAIN_VALIDATION_PLAN.md",
        "docs/TERRAIN_DESIGN_PROGRESS.md",
    ]:
        source = read(relative_path)
        for obstacle_type in OBSTACLE_TYPES:
            require(
                obstacle_type in source,
                "{} missing from {}".format(obstacle_type, relative_path),
            )


def main():
    check_dynamic_obstacle_manager()
    check_config_defaults()
    check_legged_robot_gating()
    check_viewer_script()
    check_docs()
    print("Dynamic terrain static checks passed.")


if __name__ == "__main__":
    main()
