---
name: a1-task-construction
description: Explain, inspect, or extend how the default `a1` parkour task is constructed in the extreme-parkour codebase. Use when Codex needs project-local knowledge about `A1ParkourCfg`, `LeggedRobot`, task registration, terrain generation, observations, rewards, curriculum, or how to add another parkour task without scattering documentation under `docs/`.
---

# A1 Task Construction

## Overview

Use this skill to understand the current default `a1` task and to guide changes that create or modify related parkour tasks. Keep project knowledge in this skill, following the repository's Documentation Management Principles.

## Workflow

1. Read [references/a1-task-construction.md](references/a1-task-construction.md) before explaining or modifying `a1` task construction.
2. Verify current code before editing, especially these files:
   - `legged_gym/legged_gym/envs/__init__.py`
   - `legged_gym/legged_gym/envs/a1/a1_parkour_config.py`
   - `legged_gym/legged_gym/envs/base/legged_robot_config.py`
   - `legged_gym/legged_gym/envs/base/legged_robot.py`
   - `legged_gym/legged_gym/utils/terrain.py`
   - `legged_gym/legged_gym/scripts/play.py`
   - `legged_gym/legged_gym/scripts/evaluate.py`
3. When adding another parkour task, prefer a new config class and registry entry over changing the meaning of the existing `a1` task.
4. When changing terrain families, update both the terrain proportions/config and the positional dispatcher in `Terrain.make_terrain()`.
5. After related architecture, workflow, or debugging discoveries, append the new durable knowledge to this skill instead of creating standalone docs.

## Key Facts

- The CLI default task is `a1`.
- `a1` is registered as `LeggedRobot` with `A1ParkourCfg()` and `A1ParkourCfgPPO()`.
- `A1ParkourCfg` supplies A1-specific pose, PD control, URDF, contact, and reward parameter overrides.
- Most parkour behavior comes from inherited `LeggedRobotCfg`, shared `LeggedRobot`, and `Terrain`.
- `play.py` and `evaluate.py` override terrain distribution during testing, so task changes may need matching updates there.

## Cautions

- Do not rely on adding a key to `terrain_dict` alone. The ordered values become `terrain_proportions`, and `Terrain.make_terrain()` interprets cumulative ranges by fixed position.
- Do not update copied or stale files under `legged_gym/legged_gym/scripts/legged_gym/` unless runtime inspection proves they are active.
- Do not create new standalone Markdown docs for this subsystem unless the user explicitly asks. Add durable notes to this skill.

## Reference

The detailed construction notes live in [references/a1-task-construction.md](references/a1-task-construction.md).
