---
name: a1-dynamic-task-design
description: Use when explaining, inspecting, tuning, or extending the `a1_dynamic` dynamic-obstacle parkour task design in extreme-parkour, including `A1DynamicParkourCfg`, `DynamicLeggedRobot`, task registration, dynamic terrain generation, scripted obstacle actors, moving goals, dynamic height scans, rewards, curriculum, and static A1 counterparts used as design references.
---

# A1 Dynamic Task Design

## Overview

Use this skill to understand and modify the `a1_dynamic` task: a dynamic-obstacle extension of A1 parkour with scripted moving hurdles, gaps, tilted pads, steps, and mixed demo tracks. The static `a1` task is documented here only as a design reference and compatibility baseline.

## Workflow

1. Read [references/a1-dynamic-task-design.md](references/a1-dynamic-task-design.md) before explaining or modifying `a1_dynamic` task construction.
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
3. Keep `a1_dynamic` separate from `a1`: prefer dynamic-specific config, metadata, actors, and registry entries over changing static-task semantics.
4. When changing dynamic terrain families, update both the terrain proportions/config and the positional dispatcher in `Terrain.make_terrain()`.
5. For training-pipeline work involving static A1 expert imitation before `a1_dynamic` base RL fine-tuning, read `skills/imitation-pretraining/SKILL.md`.
6. For the next-stage latent-state or distillation pipeline, read `skills/improved-training-pipeline/SKILL.md`.

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
- Preserve the one-robot-actor semantics used by the base task when adding additional dynamic actors; resets and pushes should address robot actor indices rather than all root states.

## Reference

The detailed construction notes live in [references/a1-dynamic-task-design.md](references/a1-dynamic-task-design.md).
