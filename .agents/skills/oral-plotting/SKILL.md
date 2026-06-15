---
name: oral-plotting
description: Use when creating, modifying, or validating plots for the extreme-parkour oral presentation or future report, especially scripts under `oral/figures`, PDF plot outputs, consistent training-pipeline colors, missing eval CSV handling, and per-target Makefile integration.
---

# Oral Plotting

## Overview

Use this skill for presentation/report plots. Keep reusable project-wide plot scripts under `plots/`; keep oral-specific plotting scripts and generated figures under `oral/figures`.

## Workflow

1. Output PDF plots for slides.
2. Create one plotting script per figure to avoid unnecessary regeneration.
3. Add one Makefile target per plotting script.
4. Use available `metrics.csv`, `metrics_all.csv`, or `imitation_metrics.csv` files; do not fabricate unavailable CSV data.
5. If an experiment directory exists but is empty, leave a `% TODO(missing-data): ...` in the consuming TeX and ask the user for the intended analysis.
6. For multi-pipeline comparisons, show smoothed curves only; avoid raw curves and error bars.
7. For single-pipeline evaluation plots, show error bars and smoothed curves.
8. For camera-distillation training curves, draw a horizontal dashed line in the same color as each pipeline for the corresponding base-RL performance. Keep dashed lines out of the legend and explain them in the caption.

## Color Mapping

Keep colors stable across slides and future reports:

- Original static pipeline: blue.
- Original dynamic pipeline: gray.
- Imitation-pretrained dynamic pipeline: green.
- ROA dynamic latent recovery: orange.
- Teacher-student dynamic latent recovery: purple.
- Hybrid mixed-terrain recovery: red or another distinct color not already used.

## Data Interpretation

Prefer per-family evaluation for dynamic obstacle claims. Aggregate reward or waypoint count is useful for overview slides but can hide obstacle-specific failures.

## Runtime Notes

- Plotting scripts should use normal scientific Python tools such as `matplotlib`, `pandas`, and NumPy.
- Use `conda run -n daily python` from the Makefile for oral plotting.
- If plotting cannot run in the current environment, stop before running or rerunning plot targets and ask the user to run `gmake` locally or provide the generated PDFs.
- `grid.axis` is not a valid Matplotlib rcParam. For y-axis-only grids, call `ax.grid(True, axis="y", alpha=...)` in plotting code instead of setting it through `plt.rcParams`.
