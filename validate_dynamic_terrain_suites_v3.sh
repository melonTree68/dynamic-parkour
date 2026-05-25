#!/usr/bin/env bash
set -euo pipefail

RUN_RUNTIME=0
STEPS=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime)
      RUN_RUNTIME=1
      shift
      ;;
    --steps)
      STEPS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

python -m py_compile legged_gym/legged_gym/utils/dynamic_terrain_suites.py
python -m py_compile tools/plot_dynamic_terrain_layouts.py
python -m py_compile tools/check_terrain_design.py
python tools/check_terrain_design.py

python - "$RUN_RUNTIME" "$STEPS" <<'PY'
import importlib.util
import math
import sys
from pathlib import Path

run_runtime = bool(int(sys.argv[1]))
steps = int(sys.argv[2])

suite_path = Path("legged_gym/legged_gym/utils/dynamic_terrain_suites.py")
spec = importlib.util.spec_from_file_location("dynamic_terrain_suites_v3", suite_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

suites = module.DYNAMIC_TERRAIN_SUITES
expected_difficulties = ["easy", "medium", "hard", "hardest"]
minimum_counts = {
    "pure_hurdle": 4,
    "pure_step": 4,
    "pure_gap": 4,
    "pure_ramp": 4,
    "mixed": 3,
}
primitive_actor_counts = {
    "moving_hurdle": 1,
    "shifting_gap": 2,
    "changing_step_height": 1,
    "time_varying_ramp": 1,
}

for suite_name, min_count in minimum_counts.items():
    assert suite_name in suites, f"{suite_name} suite missing"
    assert len(suites[suite_name]) >= min_count, f"{suite_name} has too few layouts"

for suite_name in ["pure_hurdle", "pure_step", "pure_gap", "pure_ramp"]:
    difficulties = [layout.get("difficulty") for layout in suites[suite_name][:4]]
    assert difficulties == expected_difficulties, (
        f"{suite_name} difficulty ladder is {difficulties}"
    )

for suite_name, layouts in suites.items():
    for layout_id, layout in enumerate(layouts):
        assert layout.get("runup_length", 0.0) > 0.0, (suite_name, layout_id)
        assert layout.get("runout_length", 0.0) > 0.0, (suite_name, layout_id)
        assert layout.get("corridor_half_width", 0.0) >= 0.6, (suite_name, layout_id)
        last_x = -math.inf
        for obs in layout["obstacles"]:
            obs_type = obs["type"]
            assert obs["actor_count"] == primitive_actor_counts[obs_type]
            assert all(value > 0.0 for value in obs["size"])
            x, y, _ = obs["base_position"]
            assert abs(y) <= layout["corridor_half_width"] + 0.1
            assert x >= 0.8, (suite_name, layout_id, obs["name"])
            assert x >= last_x - 0.35, (suite_name, layout_id, obs["name"])
            last_x = max(last_x, x)

            if obs_type == "moving_hurdle":
                assert obs["size"][0] <= 0.15, obs["name"]
                assert obs["size"][1] >= 0.8, obs["name"]
            elif obs_type == "shifting_gap":
                assert obs["size"][0] >= 0.50, obs["name"]
                assert obs["edge_separation"] > obs["size"][0], obs["name"]
            elif obs_type == "time_varying_ramp":
                assert obs["size"][0] >= 1.25, obs["name"]
                assert obs["size"][1] >= 1.08, obs["name"]
                assert obs["size"][2] <= 0.05, obs["name"]

if run_runtime:
    for suite_name, layouts in suites.items():
        for layout_id, layout in enumerate(layouts):
            for step_id in range(max(0, steps)):
                t = step_id / 60.0
                for obs in layout["obstacles"]:
                    amp = sum(obs["amplitude_range"]) / 2.0
                    freq = sum(obs["frequency_range"]) / 2.0
                    phase = sum(obs["phase_range"]) / 2.0
                    offset = amp * math.sin(2.0 * math.pi * freq * t + phase)
                    assert math.isfinite(offset), (suite_name, layout_id, obs["name"])

print(
    "Dynamic terrain suite v3 validation passed "
    f"(runtime={run_runtime}, steps={steps})."
)
PY
