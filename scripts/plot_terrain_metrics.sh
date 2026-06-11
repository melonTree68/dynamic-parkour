#!/usr/bin/env bash
set -euo pipefail

terrains="hurdle gap step tilted_pads demo"

for t in $terrains; do
    conda run -n parkour python plots/plot_terrain_metrics.py "$t"
done
