import numpy as np

from isaacgym import terrain_utils

import legged_gym.envs  # Registers tasks before importing utility modules.
from legged_gym.envs.a1.a1_dynamic import DynamicLeggedRobot
from legged_gym.envs.a1.a1_dynamic_config import A1DynamicParkourCfg
from legged_gym.envs.base.legged_robot import LeggedRobot
from legged_gym.utils import task_registry
from legged_gym.utils.terrain import (
    DYNAMIC_DEMO,
    DYNAMIC_GAP,
    DYNAMIC_HURDLE,
    DYNAMIC_STEP,
    DYNAMIC_TILTED_PADS,
    dynamic_demo_terrain,
    dynamic_gap_terrain,
    dynamic_hurdle_terrain,
    dynamic_step_terrain,
    dynamic_tilted_pads_terrain,
)

DYNAMIC_CFG = A1DynamicParkourCfg.dynamic_obstacles
Y_RANGE = A1DynamicParkourCfg.terrain.y_range


def test_dynamic_task_registration_preserves_a1_configuration():
    dynamic_cfg, _ = task_registry.get_cfgs("a1_dynamic")
    static_cfg, _ = task_registry.get_cfgs("a1")
    assert task_registry.get_task_class("a1_dynamic") is DynamicLeggedRobot
    assert task_registry.get_task_class("a1") is LeggedRobot
    assert dynamic_cfg.env.num_envs == 2048
    assert static_cfg.env.n_dynamic_env_latent == 0
    assert dynamic_cfg.env.n_dynamic_env_latent == 30
    assert (
        dynamic_cfg.env.num_observations
        == static_cfg.env.num_observations + dynamic_cfg.env.n_dynamic_env_latent
    )
    assert dynamic_cfg.rewards.scales.bad_dynamic_takeoff == -1.0
    dynamic_weights = [
        dynamic_cfg.terrain.terrain_dict[name]
        for name in (
            "dynamic_hurdle",
            "dynamic_gap",
            "dynamic_tilted_pads",
            "dynamic_step",
            "dynamic_demo",
        )
    ]
    assert dynamic_weights == [0.2] * 5
    assert sum(dynamic_weights) == 1.0
    assert hasattr(dynamic_cfg.dynamic_obstacles, "hurdle_period_min")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "gap_spacing")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "step_height_max")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "tilted_pad_y_range_coeff")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "dynamic_demo_spacing")
    assert dynamic_cfg.dynamic_env_latent.num_future_groups == 2
    assert dynamic_cfg.dynamic_env_latent.features_per_group == 15


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
        (dynamic_demo_terrain, DYNAMIC_DEMO),
    ]
    for generator, family in generators:
        terrain = make_subterrain()
        generator(
            terrain,
            difficulty=0.5,
            num_goals=8,
            dynamic_cfg=DYNAMIC_CFG,
            y_range=Y_RANGE,
        )
        assert terrain.dynamic_family == family
        assert terrain.dynamic_obstacle_specs.shape == (6, 2, 7)
        assert terrain.goals.shape == (8, 2)


def test_dynamic_gap_keeps_fixed_pair_spacing_and_marks_moving_goals():
    terrain = make_subterrain()
    dynamic_gap_terrain(
        terrain, difficulty=0.7, num_goals=8, dynamic_cfg=DYNAMIC_CFG, y_range=Y_RANGE
    )
    specs = terrain.dynamic_obstacle_specs
    gap_lengths = specs[:, 1, 0] - specs[:, 0, 0] - specs[:, 0, 3]
    assert np.allclose(gap_lengths, gap_lengths[0])
    assert np.count_nonzero(terrain.dynamic_goal_mask) == 6
    assert np.all(
        terrain.dynamic_motion_types == np.array([[DYNAMIC_GAP, DYNAMIC_GAP]] * 6)
    )
    assert np.array_equal(terrain.dynamic_goal_groups[1:7], np.arange(6))
    gap_centers = (specs[:, 0, 0] + specs[:, 1, 0]) / 2
    midpoint = round(((gap_centers[0] + gap_centers[1]) / 2) / terrain.horizontal_scale)
    assert np.all(terrain.height_field_raw[midpoint] == 0)


def test_dynamic_steps_have_stochastic_progression_and_buried_bodies():
    terrain = make_subterrain()
    dynamic_step_terrain(
        terrain, difficulty=1.0, num_goals=8, dynamic_cfg=DYNAMIC_CFG, y_range=Y_RANGE
    )
    specs = terrain.dynamic_obstacle_specs[:, 0]
    top = specs[:, 2] + specs[:, 5] / 2
    assert top[0] < top[1] < top[2]
    assert top[3] <= top[2] and top[4] <= top[3] and top[5] <= top[4]
    increments = np.array([top[0], top[1] - top[0], top[2] - top[1]])
    assert np.all(increments >= DYNAMIC_CFG.step_height_min[1])
    assert np.all(increments <= DYNAMIC_CFG.step_height_max[1])
    maximum_bottom = specs[:, 2] - specs[:, 5] / 2 + DYNAMIC_CFG.step_amplitude[1]
    assert np.all(maximum_bottom <= 0.0)


def test_dynamic_layout_uses_a1_style_lateral_offsets_and_sampled_hurdle_heights():
    np.random.seed(3)
    terrain = make_subterrain()
    dynamic_hurdle_terrain(
        terrain, difficulty=1.0, num_goals=8, dynamic_cfg=DYNAMIC_CFG, y_range=Y_RANGE
    )
    specs = terrain.dynamic_obstacle_specs[:, 0]
    tops = specs[:, 2] + specs[:, 5] / 2
    y_offset = specs[:, 1] - terrain.length * terrain.horizontal_scale / 2
    assert np.all(tops >= DYNAMIC_CFG.hurdle_height_min[1])
    assert np.all(tops <= DYNAMIC_CFG.hurdle_height_max[1])
    assert np.all(y_offset >= Y_RANGE[0]) and np.all(y_offset <= Y_RANGE[1])
    assert np.allclose(terrain.goals[1:7, 1], specs[:, 1])
    assert len(np.unique(specs[:, 1])) > 1


def test_dynamic_spacing_ranges_are_configurable_per_family():
    cases = [
        (dynamic_hurdle_terrain, DYNAMIC_CFG.hurdle_spacing, 0.0, 0.0),
        (dynamic_gap_terrain, DYNAMIC_CFG.gap_spacing, DYNAMIC_CFG.gap_size[1], 0.0),
        (
            dynamic_tilted_pads_terrain,
            DYNAMIC_CFG.tilted_pad_spacing,
            0.0,
            DYNAMIC_CFG.tilted_pad_dims[0],
        ),
        (dynamic_step_terrain, DYNAMIC_CFG.step_spacing, 0.0, DYNAMIC_CFG.step_dims[0]),
    ]
    for generator, spacing, event_width, body_length in cases:
        terrain = make_subterrain()
        generator(
            terrain,
            difficulty=1.0,
            num_goals=8,
            dynamic_cfg=DYNAMIC_CFG,
            y_range=Y_RANGE,
        )
        centers = terrain.dynamic_obstacle_specs[:, 0, 0]
        sampled_spacing = np.diff(centers) - event_width - body_length
        assert np.all(sampled_spacing >= spacing[0])
        assert np.all(sampled_spacing <= spacing[1])


def test_dynamic_demo_has_mixed_motion_sequence_and_gap_goal_mapping():
    terrain = make_subterrain()
    dynamic_demo_terrain(
        terrain, difficulty=0.5, num_goals=8, dynamic_cfg=DYNAMIC_CFG, y_range=Y_RANGE
    )
    types = terrain.dynamic_motion_types
    assert types[0, 0] == DYNAMIC_HURDLE
    assert types[1, 0] == DYNAMIC_STEP
    assert np.array_equal(types[2], [DYNAMIC_GAP, DYNAMIC_GAP])
    assert types[3, 0] == DYNAMIC_TILTED_PADS
    assert types[4, 0] == DYNAMIC_TILTED_PADS
    assert np.array_equal(terrain.dynamic_obstacle_specs[3:5, 0, 6], [1.0, -1.0])
    mid_y = terrain.length * terrain.horizontal_scale / 2
    assert np.all(
        (terrain.dynamic_obstacle_specs[3:5, 0, 1] - mid_y)
        * terrain.dynamic_obstacle_specs[3:5, 0, 6]
        >= 0.0
    )
    assert np.array_equal(terrain.dynamic_goal_groups[3:5], [2, 2])


def test_dynamic_demo_uses_own_spacing_ranges():
    old_spacing = DYNAMIC_CFG.dynamic_demo_spacing
    DYNAMIC_CFG.dynamic_demo_spacing = [
        [0.50, 0.55],
        [0.60, 0.65],
        [0.70, 0.75],
        [0.80, 0.85],
        [0.90, 0.95],
    ]
    try:
        terrain = make_subterrain()
        dynamic_demo_terrain(
            terrain,
            difficulty=1.0,
            num_goals=8,
            dynamic_cfg=DYNAMIC_CFG,
            y_range=Y_RANGE,
        )
        specs = terrain.dynamic_obstacle_specs
        gap_center = (specs[2, 0, 0] + specs[2, 1, 0]) / 2
        centers = np.array(
            [specs[0, 0, 0], specs[1, 0, 0], gap_center, specs[3, 0, 0], specs[4, 0, 0]]
        )
        sampled_spacing = np.array(
            [
                centers[0] - 2.0,
                centers[1] - centers[0] - DYNAMIC_CFG.step_dims[0],
                centers[2] - centers[1] - DYNAMIC_CFG.gap_size[1],
                centers[3] - centers[2] - DYNAMIC_CFG.tilted_pad_dims[0],
                centers[4] - centers[3] - DYNAMIC_CFG.tilted_pad_dims[0],
            ]
        )
        for sampled, bounds in zip(sampled_spacing, DYNAMIC_CFG.dynamic_demo_spacing):
            assert bounds[0] <= sampled <= bounds[1]
    finally:
        DYNAMIC_CFG.dynamic_demo_spacing = old_spacing


def test_dynamic_tilted_pads_have_alternating_fixed_roll_signs():
    terrain = make_subterrain()
    dynamic_tilted_pads_terrain(
        terrain, difficulty=0.5, num_goals=8, dynamic_cfg=DYNAMIC_CFG, y_range=Y_RANGE
    )
    assert np.array_equal(
        terrain.dynamic_obstacle_specs[:, 0, 6], [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
    )
    mid_y = terrain.length * terrain.horizontal_scale / 2
    y_offsets = terrain.dynamic_obstacle_specs[:, 0, 1] - mid_y
    assert np.all(y_offsets * terrain.dynamic_obstacle_specs[:, 0, 6] >= 0.0)
    assert np.allclose(terrain.goals[1:7, 1], terrain.dynamic_obstacle_specs[:, 0, 1])


def test_dynamic_tilted_pad_y_range_coeff_scales_lateral_offsets():
    old_coeff = DYNAMIC_CFG.tilted_pad_y_range_coeff
    DYNAMIC_CFG.tilted_pad_y_range_coeff = 0.25
    try:
        max_offset = max(abs(Y_RANGE[0]), abs(Y_RANGE[1])) * 0.25

        terrain = make_subterrain()
        dynamic_tilted_pads_terrain(
            terrain,
            difficulty=0.5,
            num_goals=8,
            dynamic_cfg=DYNAMIC_CFG,
            y_range=Y_RANGE,
        )
        mid_y = terrain.length * terrain.horizontal_scale / 2
        offsets = terrain.dynamic_obstacle_specs[:, 0, 1] - mid_y
        assert np.all(np.abs(offsets) <= max_offset + 1e-6)

        terrain = make_subterrain()
        dynamic_demo_terrain(
            terrain,
            difficulty=0.5,
            num_goals=8,
            dynamic_cfg=DYNAMIC_CFG,
            y_range=Y_RANGE,
        )
        offsets = terrain.dynamic_obstacle_specs[3:5, 0, 1] - mid_y
        assert np.all(np.abs(offsets) <= max_offset + 1e-6)
    finally:
        DYNAMIC_CFG.tilted_pad_y_range_coeff = old_coeff
