from .a1_parkour_config import A1ParkourCfg, A1ParkourCfgPPO


class A1DynamicParkourCfg(A1ParkourCfg):
    class dynamic_env_latent:
        enabled = True
        num_future_groups = 2
        features_per_group = 15
        recovery_modes = {
            "hurdle": "roa",
            "gap": "roa",
            "step": "roa",
            "tilted_pad": "roa",
        }
        roa_loss_weight = 1.0
        teacher_student_loss_weight = 1.0

    class env(A1ParkourCfg.env):
        num_envs = 2048
        n_dynamic_env_latent = A1ParkourCfg.env.n_dynamic_env_latent + 2 * 15
        num_observations = A1ParkourCfg.env.num_observations + n_dynamic_env_latent

    class terrain(A1ParkourCfg.terrain):
        y_range = [-0.4, 0.4]
        terrain_dict = {
            "smooth slope": 0.0,
            "rough slope up": 0.0,
            "rough slope down": 0.0,
            "rough stairs up": 0.0,
            "rough stairs down": 0.0,
            "discrete": 0.0,
            "stepping stones": 0.0,
            "gaps": 0.0,
            "smooth flat": 0.0,
            "pit": 0.0,
            "wall": 0.0,
            "platform": 0.0,
            "large stairs up": 0.0,
            "large stairs down": 0.0,
            "parkour": 0.0,
            "parkour_hurdle": 0.0,
            "parkour_flat": 0.0,
            "parkour_step": 0.0,
            "parkour_gap": 0.0,
            "demo": 0.0,
            "dynamic_hurdle": 0.2,
            "dynamic_gap": 0.2,
            "dynamic_tilted_pads": 0.2,
            "dynamic_step": 0.2,
            "dynamic_demo": 0.2,
            "mixed_demo": 0.0,
            "mixed_tilted_pads": 0.0,
            "mixed_hurdle": 0.0,
        }
        terrain_proportions = list(terrain_dict.values())

    class dynamic_obstacles:
        num_obstacles = 6
        slots_per_obstacle = 2
        inactive_z = -5.0

        hurdle_thickness = 0.20
        hurdle_width = 1.10
        hurdle_height_min = [0.10, 0.20]
        hurdle_height_max = [0.15, 0.40]
        hurdle_spacing = [1.2, 2.2]

        gap_size = [0.10, 0.80]
        gap_platform_dims = [0.55, 1.60, 0.10]
        gap_spacing = [1.4, 2.5]

        tilted_pad_dims = [0.75, 1.35, 0.10]
        tilted_pad_spacing = [-0.1, 0.4]
        tilted_pad_y_range_coeff = 2.5

        step_dims = [0.80, 1.45]
        step_height_min = [0.10, 0.40]
        step_height_max = [0.10, 0.50]
        step_spacing = [0.1, 0.3]

        dynamic_demo_spacing = [
            [1.0, 1.5],  # start -> hurdle
            [1.0, 1.5],  # hurdle -> step
            [1.5, 2.5],  # step -> gap
            [1.5, 2.0],  # gap -> tilted pad 1
            [-0.1, 0.4],  # tilted pad 1 -> tilted pad 2
        ]

        hurdle_amplitude = [0.02, 0.12]
        gap_amplitude = [0.05, 0.30]
        tilted_pad_amplitude = [0.10, 0.45]
        step_amplitude = [0.02, 0.12]
        amplitude_min_fraction = 0.8
        tilted_pad_min_roll_fraction = 0.35

        hurdle_period_min = [4.0, 2.5]
        hurdle_period_max = [5.0, 3.0]
        gap_period_min = [3.5, 2.0]
        gap_period_max = [4.0, 2.5]
        tilted_pad_period_min = [4.0, 2.5]
        tilted_pad_period_max = [4.5, 3.0]
        step_period_min = [3.7, 2.5]
        step_period_max = [4.5, 3.0]

    class rewards(A1ParkourCfg.rewards):
        class scales(A1ParkourCfg.rewards.scales):
            bad_dynamic_takeoff = -1.0


class A1DynamicParkourCfgPPO(A1ParkourCfgPPO):
    class runner(A1ParkourCfgPPO.runner):
        run_name = ""
        experiment_name = "a1_dynamic"


class A1MixedParkourCfg(A1DynamicParkourCfg):
    class terrain(A1DynamicParkourCfg.terrain):
        terrain_dict = {
            **A1DynamicParkourCfg.terrain.terrain_dict,
            "dynamic_hurdle": 0.0,
            "dynamic_gap": 0.2,
            "dynamic_tilted_pads": 0.0,
            "dynamic_step": 0.0,
            "dynamic_demo": 0.0,
            "parkour_step": 0.2,
            "mixed_demo": 0.2,
            "mixed_tilted_pads": 0.2,
            "mixed_hurdle": 0.2,
        }
        terrain_proportions = list(terrain_dict.values())


class A1MixedParkourCfgPPO(A1DynamicParkourCfgPPO):
    class runner(A1DynamicParkourCfgPPO.runner):
        run_name = ""
        experiment_name = "a1_mixed"
