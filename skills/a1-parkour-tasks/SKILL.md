---
name: a1-parkour-tasks
description: Explain, inspect, tune, or extend how the default `a1` parkour task and the derived `a1_dynamic` task are constructed in the extreme-parkour codebase. Use when Codex needs project-local knowledge about `A1ParkourCfg`, `A1DynamicParkourCfg`, `LeggedRobot`, `DynamicLeggedRobot`, task registration, terrain generation, observations, rewards, curriculum, scripted dynamic obstacle actors, or how to add another parkour task without scattering documentation under `docs/`.
---

# A1 Parkour Tasks

## Overview

Use this skill to understand the current default `a1` task and to guide changes that create, tune, or modify related parkour tasks such as `a1_dynamic`. Keep project knowledge in this skill, following the repository's Documentation Management Principles.

## Workflow

1. Read [references/a1-parkour-tasks.md](references/a1-parkour-tasks.md) before explaining or modifying `a1` or `a1_dynamic` task construction.
2. Verify current code before editing, especially these files:
   - `legged_gym/legged_gym/envs/__init__.py`
   - `legged_gym/legged_gym/envs/a1/a1_parkour_config.py`
   - `legged_gym/legged_gym/envs/a1/a1_dynamic_config.py`
   - `legged_gym/legged_gym/envs/a1/a1_dynamic.py`
   - `legged_gym/legged_gym/envs/base/legged_robot_config.py`
   - `legged_gym/legged_gym/envs/base/legged_robot.py`
   - `legged_gym/legged_gym/utils/terrain.py`
   - `legged_gym/legged_gym/scripts/play.py`
   - `legged_gym/legged_gym/scripts/evaluate.py`
3. When adding another parkour task, prefer a new config class and registry entry over changing the meaning of the existing `a1` task.
4. When changing terrain families, update both the terrain proportions/config and the positional dispatcher in `Terrain.make_terrain()`.
5. For training-pipeline work involving static A1 expert imitation before `a1_dynamic` base RL fine-tuning, read `skills/imitation-pretraining/SKILL.md`.

## Key Facts

- The CLI default task is `a1_dynamic`.
- `a1` is registered as `LeggedRobot` with `A1ParkourCfg()` and `A1ParkourCfgPPO()`.
- `A1ParkourCfg` supplies A1-specific pose, PD control, URDF, contact, and reward parameter overrides.
- `a1_dynamic` is registered separately from `a1` as `DynamicLeggedRobot` with `A1DynamicParkourCfg()` and `A1DynamicParkourCfgPPO()`.
- `A1DynamicParkourCfg` inherits from `A1ParkourCfg`; tune user-facing dynamic obstacle parameters in `legged_gym/legged_gym/envs/a1/a1_dynamic_config.py`.
- Most parkour behavior comes from inherited `LeggedRobotCfg`, shared `LeggedRobot`, and `Terrain`.
- `play.py` and `evaluate.py` override terrain distribution during testing, so task changes may need matching updates there.
- `a1_dynamic` can be imitation-pretrained from a static A1 expert before the original base RL training stage; see `skills/imitation-pretraining/SKILL.md`.

## Cautions

- Do not rely on adding a key to `terrain_dict` alone. The ordered values become `terrain_proportions`, and `Terrain.make_terrain()` interprets cumulative ranges by fixed position.
- Do not update copied or stale files under `legged_gym/legged_gym/scripts/legged_gym/` unless runtime inspection proves they are active.

## Reference

The detailed construction notes live in [references/a1-parkour-tasks.md](references/a1-parkour-tasks.md).
