---
name: imitation-pretraining
description: Use when modifying, running, or explaining the imitation pretraining stage for `a1_dynamic`, including static A1 expert loading, DAgger behavior cloning, replay-buffer settings, imitation metrics, checkpoint compatibility with base RL fine-tuning, or the full static-expert to dynamic-policy training pipeline.
---

# Imitation Pretraining

## Overview

`a1_dynamic` is hard to learn from scratch with base RL. The pretraining pipeline uses a static-terrain `a1` base policy as an expert to initialize an `a1_dynamic` policy through imitation learning before the original base RL training stage.

Pipeline:

1. Static A1 expert.
2. `a1_dynamic` imitation pretraining.
3. Base RL fine-tuning on `a1_dynamic`.
4. Camera distillation.

The base RL fine-tuning stage is the original base policy training stage, resumed from an imitation checkpoint.

## Workflow

- Use `legged_gym/legged_gym/scripts/pretrain_imitation.py` for imitation pretraining.
- Use `scripts/pretrain_imitation.sh` as the project command record for the imitation pretraining stage and the following base RL fine-tune command.
- The default expert is the latest checkpoint under `legged_gym/logs/original-pipeline-static-terrain/base`.
- Student initialization defaults to `scratch`; use `--student_init expert` only when intentionally comparing to direct static-policy fine-tuning.
- Imitation checkpoints are saved as normal `model_*.pt` files under `legged_gym/logs/<proj_name>/<exptid>/` and can be consumed by `train.py --resume`.
- Metrics are appended to `imitation_metrics.csv` in the run directory and include only imitation-learning metrics such as action imitation loss, history-branch imitation loss, estimator loss, replay sizes, and teacher/student sample counts.

## Design Notes

- Distributional shift is expected to be severe because the expert was trained on static parkour while the student observes dynamic parkour.
- DAgger is used instead of naive offline behavior cloning: one teacher-driven BC iteration is followed by iterations that collect both teacher-driven and student-driven observations.
- During DAgger updates, replay batches use a 1:1 split between teacher-observation and student-observation samples when both partitions are non-empty.
- Expert labels use `hist_encoding=True`, matching the existing play/evaluate inference path.
- The student actor is trained in both privileged and history-encoding modes, and the estimator is trained on collected observations so later RL fine-tuning resumes through the normal training path.

## Reporting Notes

- For the midterm report, describe this as DAgger-style imitation pretraining from a static-terrain A1 expert before dynamic base RL fine-tuning.
- The relevant imitation run is `legged_gym/logs/imitation-pretrain-dynamic-terrain/imitate-base-15k/`, whose `imitation_metrics.csv` reaches action loss about `0.119`, history-action loss about `0.106`, and estimator loss about `0.105` at checkpoint `964`.
- The follow-up fine-tuning run is `legged_gym/logs/imitation-pretrain-dynamic-terrain/resume-from-base-15k/`. In the midterm-writing pass, it reached a best observed `num_waypoints_mean` of about `0.704`, compared with about `0.399` for dynamic base training from scratch.
- Treat these values as preliminary and log-derived; rerun the plot script or recompute summaries if newer completed runs are added.

## Common Commands

From `legged_gym/legged_gym/scripts` after sourcing the project runtime:

```bash
python pretrain_imitation.py --headless --task a1_dynamic --proj_name imitation-pretrain-dynamic-terrain --exptid pretrain
```

For a tiny smoke run:

```bash
python pretrain_imitation.py --debug --no_wandb --task a1_dynamic --proj_name imitation-debug --exptid smoke --max_iterations 2
```
