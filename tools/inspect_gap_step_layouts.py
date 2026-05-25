#!/usr/bin/env python3
"""Inspect and optionally view pure_gap / pure_step terrain layouts."""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE_FILE = ROOT / "legged_gym/legged_gym/utils/dynamic_terrain_suites.py"
VIEWER = ROOT / "legged_gym/legged_gym/scripts/view_dynamic_terrain.py"


def load_suites():
    spec = importlib.util.spec_from_file_location(
        "dynamic_terrain_suites_direct", SUITE_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DYNAMIC_TERRAIN_SUITES


def print_layout(suite_name, layout_id, layout):
    print("=" * 80)
    print(f"Suite: {suite_name}")
    print(f"Layout id: {layout_id}")
    print(f"Layout name: {layout.get('name')}")
    print("-" * 80)

    for obs_id, obs in enumerate(layout["obstacles"]):
        print(f"Obstacle {obs_id}")
        print(f"  name: {obs.get('name')}")
        print(f"  type: {obs.get('type')}")
        print(f"  actor_count: {obs.get('actor_count')}")
        print(f"  base_position: {obs.get('base_position')}")
        print(f"  size: {obs.get('size')}")
        print(f"  motion_axis: {obs.get('motion_axis')}")
        print(f"  amplitude_range: {obs.get('amplitude_range')}")
        print(f"  frequency_range: {obs.get('frequency_range')}")
        print(f"  phase_range: {obs.get('phase_range')}")

        if obs.get("type") == "shifting_gap":
            print(f"  edge_separation: {obs.get('edge_separation')}")
            print(
                "  semantics: two moving takeoff/landing platform actors, not a real mesh hole"
            )

        if obs.get("type") == "changing_step_height":
            print(f"  step_height: {obs.get('step_height')}")
            print("  semantics: fixed-size step actor moving vertically in z")

        print()


def view_layout(suite_name, layout_id, steps, rows, cols, headless):
    cmd = [
        sys.executable,
        str(VIEWER),
        "--task",
        "a1",
        "--suite",
        suite_name,
        "--layout_id",
        str(layout_id),
        "--steps",
        str(steps),
        "--rows",
        str(rows),
        "--cols",
        str(cols),
    ]

    if headless:
        cmd.append("--headless")

    print("=" * 80)
    print("Running viewer/debug command:")
    print(" ".join(cmd))
    print("=" * 80)

    subprocess.run(cmd, cwd=str(ROOT), check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite",
        choices=["pure_gap", "pure_step", "both"],
        default="both",
        help="Which suite to inspect.",
    )
    parser.add_argument(
        "--layout_id",
        type=int,
        default=None,
        help="Inspect only one layout id. Default: all layouts.",
    )
    parser.add_argument(
        "--view",
        action="store_true",
        help="Open viewer/debug script for the selected layout. Use with --layout_id.",
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--steps", type=int, default=800)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=2)
    args = parser.parse_args()

    suites = load_suites()

    suite_names = ["pure_gap", "pure_step"] if args.suite == "both" else [args.suite]

    for suite_name in suite_names:
        layouts = suites[suite_name]

        if args.layout_id is None:
            layout_ids = range(len(layouts))
        else:
            if args.layout_id < 0 or args.layout_id >= len(layouts):
                raise SystemExit(
                    f"Invalid layout_id={args.layout_id} for {suite_name}. "
                    f"Valid range: 0..{len(layouts) - 1}"
                )
            layout_ids = [args.layout_id]

        for layout_id in layout_ids:
            print_layout(suite_name, layout_id, layouts[layout_id])

            if args.view:
                if args.layout_id is None:
                    raise SystemExit(
                        "--view requires --layout_id to avoid opening many viewers"
                    )
                view_layout(
                    suite_name=suite_name,
                    layout_id=layout_id,
                    steps=args.steps,
                    rows=args.rows,
                    cols=args.cols,
                    headless=args.headless,
                )


if __name__ == "__main__":
    main()
