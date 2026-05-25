"""Dynamic terrain suite/layout definitions.

Layouts are deliberately data-only: the manager turns these obstacle specs into
Isaac Gym box actors while keeping static heightfields and triangle meshes
unchanged.
"""


def hurdle(name, x, y, z, axis, amp, freq, phase, length=1.0, thickness=0.08, height=0.35):
    return {
        "name": name,
        "type": "moving_hurdle",
        "actor_count": 1,
        "base_position": [x, y, z],
        "size": [length, thickness, height],
        "motion_axis": axis,
        "amplitude_range": amp,
        "frequency_range": freq,
        "phase_range": phase,
    }


def step(name, x, y, z, amp, freq, phase, length=0.6, width=1.0, height=0.18):
    return {
        "name": name,
        "type": "changing_step_height",
        "actor_count": 1,
        "base_position": [x, y, z],
        "size": [length, width, height],
        "motion_axis": "z",
        "amplitude_range": amp,
        "frequency_range": freq,
        "phase_range": phase,
        "step_height": height,
    }


def gap(name, x, y, z, axis, amp, freq, phase, separation=0.75, length=0.08, width=1.0, height=0.08):
    return {
        "name": name,
        "type": "shifting_gap",
        "actor_count": 2,
        "base_position": [x, y, z],
        "size": [length, width, height],
        "motion_axis": axis,
        "edge_separation": separation,
        "amplitude_range": amp,
        "frequency_range": freq,
        "phase_range": phase,
    }


def ramp(name, x, y, z, amp, freq, phase, base_pitch=0.15, length=0.9, width=1.0, thickness=0.08):
    return {
        "name": name,
        "type": "time_varying_ramp",
        "actor_count": 1,
        "base_position": [x, y, z],
        "size": [length, width, thickness],
        "motion_axis": "pitch",
        "base_pitch": base_pitch,
        "amplitude_range": amp,
        "frequency_range": freq,
        "phase_range": phase,
    }


DYNAMIC_TERRAIN_SUITES = {
    "pure_hurdle": [
        {
            "name": "hurdle_lateral_close",
            "obstacles": [
                hurdle("hurdle_y_short", 1.8, 0.0, 0.35, "y", [0.10, 0.25], [0.10, 0.30], [0.0, 6.28318530718]),
            ],
        },
        {
            "name": "hurdle_lateral_far",
            "obstacles": [
                hurdle("hurdle_y_wide", 2.4, 0.0, 0.35, "y", [0.20, 0.40], [0.15, 0.45], [0.0, 6.28318530718]),
            ],
        },
        {
            "name": "hurdle_forward_sweep",
            "obstacles": [
                hurdle("hurdle_x_slow", 2.2, 0.0, 0.35, "x", [0.08, 0.20], [0.08, 0.25], [0.0, 6.28318530718]),
            ],
        },
        {
            "name": "hurdle_pair_staggered",
            "obstacles": [
                hurdle("hurdle_pair_a", 1.8, -0.2, 0.32, "y", [0.10, 0.22], [0.10, 0.30], [0.0, 3.14159265359], height=0.30),
                hurdle("hurdle_pair_b", 2.8, 0.2, 0.38, "y", [0.10, 0.28], [0.12, 0.35], [3.14159265359, 6.28318530718], height=0.38),
            ],
        },
    ],
    "pure_step": [
        {
            "name": "step_low_pulse",
            "obstacles": [
                step("step_low", 2.0, 0.0, 0.14, [0.02, 0.08], [0.05, 0.20], [0.0, 6.28318530718], height=0.14),
            ],
        },
        {
            "name": "step_tall_pulse",
            "obstacles": [
                step("step_tall", 2.4, 0.0, 0.22, [0.03, 0.12], [0.08, 0.25], [0.0, 6.28318530718], height=0.22),
            ],
        },
        {
            "name": "step_narrow_offset",
            "obstacles": [
                step("step_offset", 2.2, -0.25, 0.18, [0.02, 0.10], [0.05, 0.25], [0.0, 6.28318530718], width=0.65),
            ],
        },
        {
            "name": "step_pair",
            "obstacles": [
                step("step_pair_a", 1.8, -0.2, 0.15, [0.02, 0.08], [0.08, 0.22], [0.0, 3.14159265359], height=0.15),
                step("step_pair_b", 2.8, 0.2, 0.22, [0.03, 0.10], [0.08, 0.25], [3.14159265359, 6.28318530718], height=0.22),
            ],
        },
    ],
    "pure_gap": [
        {
            "name": "gap_forward_shift",
            "obstacles": [
                gap("gap_x", 2.2, 0.0, 0.08, "x", [0.05, 0.18], [0.05, 0.20], [0.0, 6.28318530718]),
            ],
        },
        {
            "name": "gap_lateral_shift",
            "obstacles": [
                gap("gap_y", 2.3, 0.0, 0.08, "y", [0.08, 0.25], [0.08, 0.28], [0.0, 6.28318530718]),
            ],
        },
        {
            "name": "gap_wide_slow",
            "obstacles": [
                gap("gap_wide", 2.6, 0.0, 0.08, "x", [0.05, 0.15], [0.04, 0.16], [0.0, 6.28318530718], separation=0.95),
            ],
        },
        {
            "name": "gap_pair_staggered",
            "obstacles": [
                gap("gap_pair_a", 1.8, -0.2, 0.08, "x", [0.04, 0.12], [0.05, 0.18], [0.0, 3.14159265359], separation=0.65),
                gap("gap_pair_b", 3.0, 0.2, 0.08, "y", [0.05, 0.18], [0.05, 0.22], [3.14159265359, 6.28318530718], separation=0.75),
            ],
        },
    ],
    "pure_ramp": [
        {
            "name": "ramp_soft_pitch",
            "obstacles": [
                ramp("ramp_soft", 2.0, 0.0, 0.12, [0.03, 0.10], [0.05, 0.18], [0.0, 6.28318530718], base_pitch=0.10),
            ],
        },
        {
            "name": "ramp_steep_pitch",
            "obstacles": [
                ramp("ramp_steep", 2.4, 0.0, 0.14, [0.06, 0.18], [0.08, 0.25], [0.0, 6.28318530718], base_pitch=0.18),
            ],
        },
        {
            "name": "ramp_reverse_bias",
            "obstacles": [
                ramp("ramp_reverse", 2.3, 0.0, 0.12, [0.04, 0.14], [0.05, 0.20], [0.0, 6.28318530718], base_pitch=-0.10),
            ],
        },
        {
            "name": "ramp_pair",
            "obstacles": [
                ramp("ramp_pair_a", 1.8, -0.2, 0.12, [0.03, 0.12], [0.06, 0.20], [0.0, 3.14159265359], base_pitch=0.12),
                ramp("ramp_pair_b", 2.9, 0.2, 0.12, [0.04, 0.14], [0.06, 0.22], [3.14159265359, 6.28318530718], base_pitch=-0.08),
            ],
        },
    ],
    "mixed": [
        {
            "name": "mixed_hurdle_step",
            "obstacles": [
                hurdle("mixed_hurdle", 1.8, -0.15, 0.33, "y", [0.10, 0.25], [0.10, 0.30], [0.0, 6.28318530718], height=0.32),
                step("mixed_step", 2.8, 0.2, 0.18, [0.03, 0.10], [0.06, 0.22], [0.0, 6.28318530718]),
            ],
        },
        {
            "name": "mixed_gap_ramp",
            "obstacles": [
                gap("mixed_gap", 1.9, -0.15, 0.08, "x", [0.05, 0.15], [0.05, 0.18], [0.0, 6.28318530718], separation=0.75),
                ramp("mixed_ramp", 3.0, 0.2, 0.12, [0.04, 0.14], [0.06, 0.22], [0.0, 6.28318530718], base_pitch=0.12),
            ],
        },
        {
            "name": "mixed_all_primitives",
            "obstacles": [
                hurdle("mixed_all_hurdle", 1.5, -0.25, 0.32, "y", [0.08, 0.22], [0.10, 0.28], [0.0, 6.28318530718], height=0.30),
                gap("mixed_all_gap", 2.2, 0.15, 0.08, "x", [0.04, 0.14], [0.05, 0.18], [0.0, 6.28318530718], separation=0.70),
                step("mixed_all_step", 3.0, -0.15, 0.18, [0.02, 0.09], [0.06, 0.22], [0.0, 6.28318530718]),
                ramp("mixed_all_ramp", 3.8, 0.2, 0.12, [0.03, 0.12], [0.05, 0.20], [0.0, 6.28318530718], base_pitch=0.10),
            ],
        },
    ],
}


def suite_names():
    return tuple(DYNAMIC_TERRAIN_SUITES.keys())


def get_suite_layouts(suite):
    if suite not in DYNAMIC_TERRAIN_SUITES:
        raise ValueError(
            "Unknown dynamic terrain suite '{}'. Supported suites are {}.".format(
                suite, suite_names()
            )
        )
    return DYNAMIC_TERRAIN_SUITES[suite]


def layout_actor_count(layout):
    return sum(obstacle["actor_count"] for obstacle in layout["obstacles"])


def max_suite_actor_count(suite):
    return max(layout_actor_count(layout) for layout in get_suite_layouts(suite))
