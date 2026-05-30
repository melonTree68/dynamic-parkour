---
name: midterm-report-writing
description: Use when writing, updating, building, or explaining the `midterm_report` mini-paper for the extreme-parkour project, including RSS/IEEE LaTeX formatting, report figures, valid experiment logs, author/title requirements, scope-change rationale, and preliminary result values.
---

# Midterm Report Writing

## Overview

Use this skill for the course midterm report under `midterm_report/`. The report is a mini paper about dynamic-obstacle quadruped parkour. Keep durable report knowledge here instead of adding scattered notes elsewhere.

## Required Report Facts

- Source file: `midterm_report/paper_template.tex`.
- PDF target: `midterm_report/paper_template.pdf`.
- Title: `Dynamic-Obstacle Parkour with Quadruped Robots`.
- Authors, in order: Zhijie Chen and Shiyi Xiao.
- Affiliation: Shanghai Jiao Tong University.
- Emails: `zhijie.chen@sjtu.edu.cn`, `sjtuxsy-finance-pc@sjtu.edu.cn`.
- Do not label equal contribution.
- Use the RSS/IEEE template style with `natbib` and `plainnat`.
- Build through GNU Make from `midterm_report/`:

```bash
gmake
```

The Makefile should run `pdflatex` with `-synctex=1 -interaction=nonstopmode -file-line-error`, then `bibtex`, then rerun `pdflatex`.

## Figure Workflow

- Put report plotting scripts and generated report figures under `midterm_report/figures/`.
- Generate plots as PDF.
- Use `conda run -n datasci-py313 python figures/plot_midterm_results.py` from `midterm_report/`.
- Keep root-level `plots/` as reference material only; do not move or edit those files for the report.
- If an image generation asset is used in the report, copy the selected generated image into `midterm_report/figures/` before referencing it.

## Canonical Narrative

- The midterm story should emphasize infrastructure progress rather than final algorithmic novelty.
- The current project type is a research project on quadruped parkour built on `Extreme Parkour with Legged Robots`.
- The robust-depth-perception branch from the proposal is dropped for now because time is limited, all experiments are simulator-only, and the intended real-world robustness validation is unavailable.
- Main implemented infrastructure:
  - `a1_dynamic` with scripted dynamic obstacle actors in Isaac Gym.
  - Unified dynamic terrain parameter tuning through `A1DynamicParkourCfg.dynamic_obstacles`.
  - Dynamic obstacle families: moving hurdles, moving gap platforms, tilting pads, moving steps, and mixed dynamic demo.
  - A video recorder with yaw-following and attached camera modes.
  - DAgger imitation pretraining from a static-terrain A1 expert before dynamic base RL fine-tuning.

## Valid Logs and Preliminary Values

Use these logs for the midterm report unless newer completed runs supersede them:

- Static reproduction base: `legged_gym/logs/original-pipeline-static-terrain/base/metrics.csv`.
- Static distillation: `legged_gym/logs/original-pipeline-static-terrain/distill-from-15k/metrics.csv`.
- Dynamic base: `legged_gym/logs/original-pipeline-dynamic-terrain/base-v2-16f4736/metrics.csv`.
- Dynamic distillation: `legged_gym/logs/original-pipeline-dynamic-terrain/distill-from-15k-v2-16f4736/metrics.csv`.
- DAgger pretraining metrics: `legged_gym/logs/imitation-pretrain-dynamic-terrain/imitate-base-15k/imitation_metrics.csv`.
- DAgger + dynamic base fine-tuning: `legged_gym/logs/imitation-pretrain-dynamic-terrain/resume-from-base-15k/metrics.csv`.

Best observed waypoint values from the midterm-writing pass:

- Static base: `0.996` at checkpoint `9500`.
- Static distill: `0.936` at checkpoint `10000`.
- Dynamic base: `0.399` at checkpoint `38500`.
- Dynamic distill: `0.192` at checkpoint `7000`; this run is incomplete.
- DAgger + dynamic base: `0.704` at checkpoint `17500`.

## Writing Guidance

- Describe dynamic distillation conservatively because the run has not completed.
- State negative or incomplete results directly: dynamic terrain is harder, and RL from scratch underperforms static terrain.
- Use DAgger pseudocode for the implementation, not a generic algorithm summary:
  teacher-driven BC warmup, teacher and student rollout collection, expert labels for both replay partitions, balanced replay sampling, action/history-action/estimator losses, checkpointing, then RL fine-tuning.
- Keep the final report between one and four pages; if it exceeds four pages, shorten prose before dropping required sections or figures.
