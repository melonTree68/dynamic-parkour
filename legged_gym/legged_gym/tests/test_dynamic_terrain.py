import types

import numpy as np

from isaacgym import terrain_utils

import torch

import legged_gym.envs  # Registers tasks before importing utility modules.
from legged_gym.envs.a1.a1_dynamic import DynamicLeggedRobot
from legged_gym.envs.a1.a1_dynamic_config import A1DynamicParkourCfg, A1MixedParkourCfg
from legged_gym.envs.base.legged_robot import LeggedRobot
from legged_gym.utils import task_registry
from legged_gym.utils.terrain import (
    DYNAMIC_DEMO,
    DYNAMIC_MIXED_DEMO,
    DYNAMIC_MIXED_HURDLE,
    DYNAMIC_MIXED_TILTED_PADS,
    DYNAMIC_GAP,
    DYNAMIC_HURDLE,
    DYNAMIC_NONE,
    DYNAMIC_STEP,
    DYNAMIC_TILTED_PADS,
    dynamic_demo_terrain,
    dynamic_gap_terrain,
    dynamic_hurdle_terrain,
    mixed_demo_terrain,
    mixed_hurdle_terrain,
    mixed_tilted_pads_terrain,
    dynamic_step_terrain,
    dynamic_tilted_pads_terrain,
    Terrain,
)

DYNAMIC_CFG = A1DynamicParkourCfg.dynamic_obstacles
Y_RANGE = A1DynamicParkourCfg.terrain.y_range


def test_dynamic_task_registration_preserves_a1_configuration():
    dynamic_cfg, _ = task_registry.get_cfgs("a1_dynamic")
    mixed_cfg, _ = task_registry.get_cfgs("a1_mixed")
    static_cfg, _ = task_registry.get_cfgs("a1")
    assert task_registry.get_task_class("a1_dynamic") is DynamicLeggedRobot
    assert task_registry.get_task_class("a1_mixed") is DynamicLeggedRobot
    assert task_registry.get_task_class("a1") is LeggedRobot
    assert dynamic_cfg.env.num_envs == 2048
    assert mixed_cfg.env.num_envs == dynamic_cfg.env.num_envs
    assert static_cfg.env.n_dynamic_env_latent == 0
    assert dynamic_cfg.env.n_dynamic_env_latent == 30
    assert mixed_cfg.env.n_dynamic_env_latent == dynamic_cfg.env.n_dynamic_env_latent
    assert (
        dynamic_cfg.env.num_observations
        == static_cfg.env.num_observations + dynamic_cfg.env.n_dynamic_env_latent
    )
    assert mixed_cfg.env.num_observations == dynamic_cfg.env.num_observations
    assert dynamic_cfg.rewards.scales.bad_dynamic_takeoff == -1.0
    assert mixed_cfg.rewards.scales.bad_dynamic_takeoff == -1.0
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
    mixed_weights = [
        mixed_cfg.terrain.terrain_dict[name]
        for name in (
            "mixed_hurdle",
            "dynamic_gap",
            "mixed_tilted_pads",
            "parkour_step",
            "mixed_demo",
        )
    ]
    assert dynamic_weights == [0.2] * 5
    assert mixed_weights == [0.2] * 5
    assert dynamic_cfg.terrain.terrain_dict["mixed_demo"] == 0.0
    assert dynamic_cfg.terrain.terrain_dict["mixed_tilted_pads"] == 0.0
    assert dynamic_cfg.terrain.terrain_dict["mixed_hurdle"] == 0.0
    assert mixed_cfg.terrain.terrain_dict["dynamic_hurdle"] == 0.0
    assert mixed_cfg.terrain.terrain_dict["dynamic_tilted_pads"] == 0.0
    assert mixed_cfg.terrain.terrain_dict["dynamic_step"] == 0.0
    assert mixed_cfg.terrain.terrain_dict["dynamic_demo"] == 0.0
    assert sum(dynamic_cfg.terrain.terrain_dict.values()) == 1.0
    assert sum(mixed_cfg.terrain.terrain_dict.values()) == 1.0
    assert hasattr(dynamic_cfg.dynamic_obstacles, "hurdle_period_min")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "gap_spacing")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "step_height_max")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "tilted_pad_y_range_coeff")
    assert hasattr(dynamic_cfg.dynamic_obstacles, "dynamic_demo_spacing")
    assert mixed_cfg.dynamic_env_latent.num_future_groups == 2
    assert mixed_cfg.dynamic_env_latent.features_per_group == 15


def make_subterrain():
    return terrain_utils.SubTerrain(
        "terrain", width=360, length=80, vertical_scale=0.005, horizontal_scale=0.05
    )


def test_dynamic_generators_create_six_crossings_and_eight_goals():
    generators = [
        (dynamic_hurdle_terrain, DYNAMIC_HURDLE),
        (mixed_hurdle_terrain, DYNAMIC_MIXED_HURDLE),
        (dynamic_gap_terrain, DYNAMIC_GAP),
        (dynamic_tilted_pads_terrain, DYNAMIC_TILTED_PADS),
        (mixed_tilted_pads_terrain, DYNAMIC_MIXED_TILTED_PADS),
        (dynamic_step_terrain, DYNAMIC_STEP),
        (dynamic_demo_terrain, DYNAMIC_DEMO),
        (mixed_demo_terrain, DYNAMIC_MIXED_DEMO),
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


def test_mixed_hurdle_matches_dynamic_hurdle_except_family_and_latent_mask():
    np.random.seed(31)
    dynamic_terrain = make_subterrain()
    dynamic_hurdle_terrain(
        dynamic_terrain,
        difficulty=0.5,
        num_goals=8,
        dynamic_cfg=DYNAMIC_CFG,
        y_range=Y_RANGE,
    )

    np.random.seed(31)
    mixed_terrain = make_subterrain()
    mixed_hurdle_terrain(
        mixed_terrain,
        difficulty=0.5,
        num_goals=8,
        dynamic_cfg=DYNAMIC_CFG,
        y_range=Y_RANGE,
    )

    assert dynamic_terrain.dynamic_family == DYNAMIC_HURDLE
    assert mixed_terrain.dynamic_family == DYNAMIC_MIXED_HURDLE
    assert np.array_equal(dynamic_terrain.height_field_raw, mixed_terrain.height_field_raw)
    assert np.allclose(dynamic_terrain.goals, mixed_terrain.goals)
    assert np.allclose(
        dynamic_terrain.dynamic_obstacle_specs, mixed_terrain.dynamic_obstacle_specs
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_motion_types, mixed_terrain.dynamic_motion_types
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_motion_groups, mixed_terrain.dynamic_motion_groups
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_goal_groups, mixed_terrain.dynamic_goal_groups
    )
    assert not np.any(dynamic_terrain.dynamic_latent_suppressed)
    assert np.all(mixed_terrain.dynamic_latent_suppressed)


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
    assert not np.any(terrain.dynamic_latent_suppressed)


def test_mixed_demo_replaces_dynamic_step_with_static_heightfield_step():
    terrain = make_subterrain()
    mixed_demo_terrain(
        terrain, difficulty=0.5, num_goals=8, dynamic_cfg=DYNAMIC_CFG, y_range=Y_RANGE
    )
    types = terrain.dynamic_motion_types
    assert terrain.dynamic_family == DYNAMIC_MIXED_DEMO
    assert terrain.goals.shape == (8, 2)
    assert types[0, 0] == DYNAMIC_HURDLE
    assert terrain.dynamic_latent_suppressed[0]
    assert not np.any(terrain.dynamic_latent_suppressed[1:])
    assert np.all(types[1] == 0)
    assert np.array_equal(types[2], [DYNAMIC_GAP, DYNAMIC_GAP])
    assert types[3, 0] == DYNAMIC_TILTED_PADS
    assert types[4, 0] == DYNAMIC_TILTED_PADS
    assert np.array_equal(terrain.dynamic_goal_groups[3:5], [2, 2])
    assert terrain.dynamic_goal_groups[2] == -1
    assert np.array_equal(terrain.dynamic_obstacle_specs[3:5, 0, 6], [1.0, -1.0])

    step_goal = terrain.goals[2]
    px = round(step_goal[0] / terrain.horizontal_scale)
    py = round(step_goal[1] / terrain.horizontal_scale)
    assert terrain.height_field_raw[px, py] == round(
        (0.1 + 0.35 * 0.5) / terrain.vertical_scale
    )
    assert np.allclose(terrain.dynamic_obstacle_specs[1, :, 2], -5.0)


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


def test_mixed_tilted_pads_match_dynamic_tilted_pads_except_family():
    np.random.seed(23)
    dynamic_terrain = make_subterrain()
    dynamic_tilted_pads_terrain(
        dynamic_terrain,
        difficulty=0.5,
        num_goals=8,
        dynamic_cfg=DYNAMIC_CFG,
        y_range=Y_RANGE,
    )

    np.random.seed(23)
    mixed_terrain = make_subterrain()
    mixed_tilted_pads_terrain(
        mixed_terrain,
        difficulty=0.5,
        num_goals=8,
        dynamic_cfg=DYNAMIC_CFG,
        y_range=Y_RANGE,
    )

    assert dynamic_terrain.dynamic_family == DYNAMIC_TILTED_PADS
    assert mixed_terrain.dynamic_family == DYNAMIC_MIXED_TILTED_PADS
    assert np.array_equal(
        dynamic_terrain.height_field_raw, mixed_terrain.height_field_raw
    )
    assert np.allclose(dynamic_terrain.goals, mixed_terrain.goals)
    assert np.allclose(
        dynamic_terrain.dynamic_obstacle_specs, mixed_terrain.dynamic_obstacle_specs
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_motion_types, mixed_terrain.dynamic_motion_types
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_motion_groups, mixed_terrain.dynamic_motion_groups
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_goal_groups, mixed_terrain.dynamic_goal_groups
    )
    assert np.array_equal(
        dynamic_terrain.dynamic_goal_mask, mixed_terrain.dynamic_goal_mask
    )


def test_mixed_tilted_pads_zero_dynamic_env_latent_features():
    env = DynamicLeggedRobot.__new__(DynamicLeggedRobot)
    env.num_envs = 2
    env.device = torch.device("cpu")
    env.num_dynamic_obstacles = 6
    env.num_dynamic_slots = 2
    env.cfg = types.SimpleNamespace(
        dynamic_env_latent=types.SimpleNamespace(features_per_group=15),
        dynamic_obstacles=types.SimpleNamespace(tilted_pad_min_roll_fraction=0.35),
    )
    env.dynamic_family = torch.tensor(
        [DYNAMIC_TILTED_PADS, DYNAMIC_MIXED_TILTED_PADS], dtype=torch.long
    )
    env.dynamic_motion_types = torch.full((2, 6, 2), DYNAMIC_NONE, dtype=torch.long)
    env.dynamic_motion_types[:, 0, 0] = DYNAMIC_TILTED_PADS
    env.dynamic_latent_suppressed = torch.zeros(2, 6, dtype=torch.bool)
    env.obstacle_root_states = torch.zeros(2, 6, 2, 13)
    env.obstacle_root_states[:, 0, 0, :3] = torch.tensor([2.0, 0.25, 0.0])
    env.dynamic_dims = torch.zeros(2, 6, 2, 3)
    env.dynamic_dims[:, 0, 0] = torch.tensor(DYNAMIC_CFG.tilted_pad_dims)
    env.dynamic_specs = torch.zeros(2, 6, 2, 7)
    env.dynamic_specs[:, 0, 0, 6] = 1.0
    env.root_states = torch.zeros(2, 13)
    env.dynamic_offset = torch.zeros(2, 6)
    env.dynamic_offset[:, 0] = 0.2
    env.dynamic_velocity = torch.zeros(2, 6)
    env.dynamic_velocity[:, 0] = 0.1
    env.dynamic_amplitude = torch.zeros(2, 6)
    env.dynamic_amplitude[:, 0] = 0.3
    env.dynamic_period = torch.ones(2, 6) * 2.5
    env.dynamic_phase = torch.zeros(2, 6)
    env.dynamic_time = torch.zeros(2)

    group_ids = torch.zeros(2, 1, dtype=torch.long)
    features = DynamicLeggedRobot._build_dynamic_env_latent_features(env, group_ids)

    assert features[0, 0, 0] == 1.0
    assert features[0, 0, 4] == 1.0
    assert torch.any(features[0, 0] != 0.0)
    assert torch.allclose(features[1, 0], torch.zeros(15))


def test_mixed_hurdle_zeroes_dynamic_env_latent_features():
    env = DynamicLeggedRobot.__new__(DynamicLeggedRobot)
    env.num_envs = 3
    env.device = torch.device("cpu")
    env.num_dynamic_obstacles = 6
    env.num_dynamic_slots = 2
    env.cfg = types.SimpleNamespace(
        dynamic_env_latent=types.SimpleNamespace(features_per_group=15),
        dynamic_obstacles=types.SimpleNamespace(tilted_pad_min_roll_fraction=0.35),
    )
    env.dynamic_family = torch.tensor(
        [DYNAMIC_HURDLE, DYNAMIC_MIXED_HURDLE, DYNAMIC_MIXED_DEMO], dtype=torch.long
    )
    env.dynamic_motion_types = torch.full((3, 6, 2), DYNAMIC_NONE, dtype=torch.long)
    env.dynamic_motion_types[:, 0, 0] = DYNAMIC_HURDLE
    env.dynamic_latent_suppressed = torch.zeros(3, 6, dtype=torch.bool)
    env.dynamic_latent_suppressed[2, 0] = True
    env.obstacle_root_states = torch.zeros(3, 6, 2, 13)
    env.obstacle_root_states[:, 0, 0, :3] = torch.tensor([2.0, 0.25, 0.1])
    env.dynamic_dims = torch.zeros(3, 6, 2, 3)
    env.dynamic_dims[:, 0, 0] = torch.tensor(
        [DYNAMIC_CFG.hurdle_thickness, DYNAMIC_CFG.hurdle_width, 0.45]
    )
    env.dynamic_specs = torch.zeros(3, 6, 2, 7)
    env.root_states = torch.zeros(3, 13)
    env.dynamic_offset = torch.zeros(3, 6)
    env.dynamic_offset[:, 0] = 0.05
    env.dynamic_velocity = torch.zeros(3, 6)
    env.dynamic_velocity[:, 0] = 0.1
    env.dynamic_amplitude = torch.zeros(3, 6)
    env.dynamic_amplitude[:, 0] = 0.12
    env.dynamic_period = torch.ones(3, 6) * 3.0
    env.dynamic_phase = torch.zeros(3, 6)
    env.dynamic_time = torch.zeros(3)

    group_ids = torch.zeros(3, 1, dtype=torch.long)
    features = DynamicLeggedRobot._build_dynamic_env_latent_features(env, group_ids)

    assert features[0, 0, 0] == 1.0
    assert features[0, 0, 1] == 1.0
    assert torch.any(features[0, 0] != 0.0)
    assert torch.allclose(features[1, 0], torch.zeros(15))
    assert torch.allclose(features[2, 0], torch.zeros(15))


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


def test_make_terrain_dispatches_mixed_demo_family():
    terrain_obj = Terrain.__new__(Terrain)
    terrain_obj.length_per_env_pixels = 360
    terrain_obj.width_per_env_pixels = 80
    terrain_obj.num_goals = 8
    terrain_obj.proportions = [0.0] * 25 + [1.0, 1.0, 1.0]
    terrain_obj.cfg = A1MixedParkourCfg.terrain
    terrain_obj.cfg.dynamic_obstacles = A1MixedParkourCfg.dynamic_obstacles

    terrain = terrain_obj.make_terrain(choice=0.5, difficulty=0.5)

    assert terrain.idx == DYNAMIC_MIXED_DEMO
    assert terrain.dynamic_family == DYNAMIC_MIXED_DEMO
    assert terrain.goals.shape == (8, 2)


def test_make_terrain_dispatches_mixed_tilted_pads_family():
    terrain_obj = Terrain.__new__(Terrain)
    terrain_obj.length_per_env_pixels = 360
    terrain_obj.width_per_env_pixels = 80
    terrain_obj.num_goals = 8
    terrain_obj.proportions = [0.0] * 26 + [1.0, 1.0]
    terrain_obj.cfg = A1MixedParkourCfg.terrain
    terrain_obj.cfg.dynamic_obstacles = A1MixedParkourCfg.dynamic_obstacles

    terrain = terrain_obj.make_terrain(choice=0.5, difficulty=0.5)

    assert terrain.idx == DYNAMIC_MIXED_TILTED_PADS
    assert terrain.dynamic_family == DYNAMIC_MIXED_TILTED_PADS
    assert terrain.goals.shape == (8, 2)


def test_make_terrain_dispatches_mixed_hurdle_family():
    terrain_obj = Terrain.__new__(Terrain)
    terrain_obj.length_per_env_pixels = 360
    terrain_obj.width_per_env_pixels = 80
    terrain_obj.num_goals = 8
    terrain_obj.proportions = [0.0] * 27 + [1.0]
    terrain_obj.cfg = A1MixedParkourCfg.terrain
    terrain_obj.cfg.dynamic_obstacles = A1MixedParkourCfg.dynamic_obstacles

    terrain = terrain_obj.make_terrain(choice=0.5, difficulty=0.5)

    assert terrain.idx == DYNAMIC_MIXED_HURDLE
    assert terrain.dynamic_family == DYNAMIC_MIXED_HURDLE
    assert terrain.goals.shape == (8, 2)
    assert np.all(terrain.dynamic_latent_suppressed)
