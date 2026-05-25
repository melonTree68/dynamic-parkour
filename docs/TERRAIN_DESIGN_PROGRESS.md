# Terrain Design Progress

The terrain design work is complete at the scaffold/MVP level. Dynamic terrain remains disabled by default so the original static terrain baseline is preserved unless explicitly enabled.

## Completed

- Added a `dynamic_obstacles` config block for enabling obstacle actors and tuning the initial obstacle set.
- Added `DynamicObstacleManager` to create, reset, update, and store state for dynamic obstacle actors.
- Implemented the first MVP obstacle type, `moving_hurdle`, with configurable base position, motion axis, sinusoidal amplitude, frequency, phase, and reset-time randomization.
- Implemented `shifting_gap` as two thin box actors that move together to represent shifting takeoff/landing boundaries without editing the terrain mesh.
- Implemented `changing_step_height` as a fixed-size step box whose center z position changes over time.
- Implemented `time_varying_ramp` as a box actor whose pitch quaternion changes over time. This is an MVP approximation rather than a true ramp mesh.
- Integrated dynamic obstacles into the `LeggedRobot` lifecycle during environment creation, reset, and per-step simulation updates.
- Added `legged_gym/legged_gym/scripts/view_dynamic_terrain.py` for one-env viewer/debug inspection without PPO training, evaluation, wandb, or policy loading.
- Added `tools/check_terrain_design.py` for lightweight static design checks.

## Remaining Validation

- Runtime viewer validation for all four dynamic obstacle MVPs.
- Collision and reset-randomization validation.
- Training and evaluation with dynamic obstacles enabled, after viewer/collision/reset validation is complete.
- Optional privileged-observation support for dynamic obstacle state.

## Viewer/Debug Reminder

Run one obstacle at a time:

```bash
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type moving_hurdle --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type shifting_gap --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type changing_step_height --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type time_varying_ramp --steps 1000
```

On WSL, prefer Windows Terminal over the VS Code terminal, keep `num_envs = 1`, and do not run training just to inspect terrain.
