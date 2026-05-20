# Terrain Design Progress

The terrain design work is complete at the scaffold/MVP level. Dynamic terrain remains disabled by default so the original static terrain baseline is preserved unless explicitly enabled.

## Completed

- Added a `dynamic_obstacles` config block for enabling obstacle actors and tuning the initial obstacle set.
- Added `DynamicObstacleManager` to create, reset, update, and store state for dynamic obstacle actors.
- Implemented the first MVP obstacle type, `moving_hurdle`, with configurable base position, motion axis, sinusoidal amplitude, frequency, phase, and reset-time randomization.
- Integrated dynamic obstacles into the `LeggedRobot` lifecycle during environment creation, reset, and per-step simulation updates.
- Reserved future obstacle interfaces for `shifting_gap`, `changing_step_height`, and `time_varying_ramp`.

## Remaining Validation

- Runtime viewer validation for moving hurdle motion.
- Collision and reset-randomization validation.
- Training and evaluation with dynamic obstacles enabled.
- Optional privileged-observation support for dynamic obstacle state.
