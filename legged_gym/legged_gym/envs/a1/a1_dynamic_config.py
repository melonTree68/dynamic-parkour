from .a1_parkour_config import A1ParkourCfg, A1ParkourCfgPPO


class A1DynamicParkourCfg(A1ParkourCfg):
    class env(A1ParkourCfg.env):
        num_envs = 2048

    class terrain(A1ParkourCfg.terrain):
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
            "dynamic_hurdle": 0.25,
            "dynamic_gap": 0.25,
            "dynamic_tilted_pads": 0.25,
            "dynamic_step": 0.25,
        }
        terrain_proportions = list(terrain_dict.values())

    class dynamic_obstacles:
        num_obstacles = 6
        slots_per_obstacle = 2
        inactive_z = -5.0
        panel_dims = [0.75, 1.35, 0.10]
        hurdle_amplitude = [0.05, 0.25]
        gap_amplitude = [0.05, 0.25]
        tilted_pad_amplitude = [0.03, 0.20]
        step_amplitude = [0.02, 0.12]
        period_min = [2.0, 1.2]
        period_max = [3.0, 2.0]

    class rewards(A1ParkourCfg.rewards):
        class scales(A1ParkourCfg.rewards.scales):
            bad_dynamic_takeoff = -1.0


class A1DynamicParkourCfgPPO(A1ParkourCfgPPO):
    class runner(A1ParkourCfgPPO.runner):
        run_name = ""
        experiment_name = "a1_dynamic"
