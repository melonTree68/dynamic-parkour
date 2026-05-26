import numpy as np

from isaacgym import terrain_utils

import legged_gym.envs  # Registers tasks before importing utility modules.
from legged_gym.envs.a1.a1_dynamic import DynamicLeggedRobot
from legged_gym.envs.base.legged_robot import LeggedRobot
from legged_gym.utils import task_registry
from legged_gym.utils.terrain import (
    DYNAMIC_GAP,
    DYNAMIC_HURDLE,
    DYNAMIC_STEP,
    DYNAMIC_TILTED_PADS,
    dynamic_gap_terrain,
    dynamic_hurdle_terrain,
    dynamic_step_terrain,
    dynamic_tilted_pads_terrain,
)


def test_dynamic_task_registration_preserves_a1_configuration():
    dynamic_cfg, _ = task_registry.get_cfgs("a1_dynamic")
    static_cfg, _ = task_registry.get_cfgs("a1")
    assert task_registry.get_task_class("a1_dynamic") is DynamicLeggedRobot
    assert task_registry.get_task_class("a1") is LeggedRobot
    assert dynamic_cfg.env.num_envs == 2048
    assert dynamic_cfg.env.num_observations == static_cfg.env.num_observations
    assert dynamic_cfg.rewards.scales.bad_dynamic_takeoff == -1.0


def make_subterrain():
    return terrain_utils.SubTerrain(
        "terrain", width=360, length=80, vertical_scale=0.005, horizontal_scale=0.05
    )


def test_dynamic_generators_create_six_crossings_and_eight_goals():
    generators = [
        (dynamic_hurdle_terrain, DYNAMIC_HURDLE),
        (dynamic_gap_terrain, DYNAMIC_GAP),
        (dynamic_tilted_pads_terrain, DYNAMIC_TILTED_PADS),
        (dynamic_step_terrain, DYNAMIC_STEP),
    ]
    for generator, family in generators:
        terrain = make_subterrain()
        generator(terrain, difficulty=0.5, num_goals=8)
        assert terrain.dynamic_family == family
        assert terrain.dynamic_obstacle_specs.shape == (6, 2, 7)
        assert terrain.goals.shape == (8, 2)


def test_dynamic_gap_keeps_fixed_pair_spacing_and_marks_moving_goals():
    terrain = make_subterrain()
    dynamic_gap_terrain(terrain, difficulty=0.7, num_goals=8)
    specs = terrain.dynamic_obstacle_specs
    gap_lengths = specs[:, 1, 0] - specs[:, 0, 0] - specs[:, 0, 3]
    assert np.allclose(gap_lengths, gap_lengths[0])
    assert np.count_nonzero(terrain.dynamic_goal_mask) == 6


def test_dynamic_steps_use_a_lowered_foundation_between_end_platforms():
    terrain = make_subterrain()
    dynamic_step_terrain(terrain, difficulty=0.5, num_goals=8)
    center_x = round(8.0 / terrain.horizontal_scale)
    assert np.all(terrain.height_field_raw[center_x] < 0)
