from .a1_parkour_config import A1ParkourCfg, A1ParkourCfgPPO


class A1DynamicParkourCfg(A1ParkourCfg):
    class env(A1ParkourCfg.env):
        num_envs = 2048

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
        }
        terrain_proportions = list(terrain_dict.values())

    class dynamic_obstacles:
        num_obstacles = 6
        slots_per_obstacle = 2
        inactive_z = -5.0

        hurdle_thickness = 0.25  # or 0.30
        hurdle_width = 1.10
        hurdle_height_min = [0.10, 0.20]
        hurdle_height_max = [0.15, 0.40]
        hurdle_spacing = [1.2, 2.2]

        gap_size = [0.10, 0.80]
        gap_platform_dims = [0.55, 1.60, 0.10]
        gap_spacing = [1.4, 2.5]

        tilted_pad_dims = [0.75, 1.35, 0.10]
        tilted_pad_spacing = [-0.1, 0.4]
        tilted_pad_y_range_coeff = 3.0

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

        hurdle_amplitude = [0.05, 0.20]
        gap_amplitude = [0.05, 0.30]
        tilted_pad_amplitude = [0.15, 0.50]
        step_amplitude = [0.02, 0.12]
        amplitude_min_fraction = 0.8
        tilted_pad_min_roll_fraction = 0.4

        hurdle_period_min = [2.0, 1.2]
        hurdle_period_max = [3.0, 2.0]
        gap_period_min = [2.0, 1.2]
        gap_period_max = [3.0, 2.0]
        tilted_pad_period_min = [2.0, 1.2]
        tilted_pad_period_max = [3.0, 2.0]
        step_period_min = [2.4, 1.4]
        step_period_max = [3.4, 2.4]

    class rewards(A1ParkourCfg.rewards):
        class scales(A1ParkourCfg.rewards.scales):
            bad_dynamic_takeoff = -1.0


class A1DynamicParkourCfgPPO(A1ParkourCfgPPO):
    class runner(A1ParkourCfgPPO.runner):
        run_name = ""
        experiment_name = "a1_dynamic"
