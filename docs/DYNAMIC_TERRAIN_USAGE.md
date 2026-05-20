# Dynamic Terrain Usage

## Current Implementation

The repository now contains a moving-hurdle dynamic obstacle MVP.

- Dynamic obstacles are disabled by default.
- The original terrain heightfield/trimesh remains static.
- No reward changes.
- No observation changes.
- No policy or PPO changes.
- No training or experiments were run in this stage.

## Enabling The MVP

In a config derived from `LeggedRobotCfg`, enable:

```python
class dynamic_obstacles(LeggedRobotCfg.dynamic_obstacles):
    enable = True
    type = "moving_hurdle"
```

For a quick manual experiment, a future script or local config override can set:

```python
env_cfg.dynamic_obstacles.enable = True
env_cfg.dynamic_obstacles.type = "moving_hurdle"
```

Do this only for a small viewer/debug run at first.

## Configuration Fields

- `enable`: global switch. Default is `False`.
- `type`: obstacle type. Currently only `"moving_hurdle"` is implemented.
- `num_obstacles_per_env`: currently must be `1`.
- `debug_draw`: reserved for future visualization helpers.
- `randomize_on_reset`: resample hurdle motion parameters for reset envs.
- `hurdle_length`: box length along x.
- `hurdle_thickness`: box thickness along y.
- `hurdle_height`: box height along z.
- `hurdle_asset_density`: density passed to Isaac Gym asset options.
- `base_position_x`: hurdle base x offset from the env origin.
- `base_position_y`: hurdle base y offset from the env origin.
- `base_position_z`: hurdle base z offset from the env origin.
- `motion_axis`: `"x"` or `"y"`.
- `amplitude_range`: reset-time sampling range in meters.
- `frequency_range`: reset-time sampling range in Hz.
- `phase_range`: reset-time sampling range in radians.
- `make_kinematic`: sets a fixed-base, gravity-disabled box scaffold and updates root state manually.
- `collision_enabled`: best-effort collision filter switch for future validation.

The base position is interpreted in local environment coordinates and then offset by `env_origin`. The default `base_position_x = 2.0` places the hurdle shortly after the robot start area without changing static parkour goals or terrain generation.

Invalid obstacle types, invalid motion axes, malformed ranges, negative frequencies, and non-positive hurdle dimensions raise errors instead of silently falling back.

## Viewer Check

This stage does not run `train.py`, `play.py`, or any evaluation script.

Later, after installing Isaac Gym and dependencies, manually run a small number of environments with a viewer to confirm:

- The `dynamic_hurdle` actor appears.
- The actor moves along the configured axis.
- Collision behavior matches expectations.
- Reset randomization changes amplitude, frequency, or phase.

Use a small env count and avoid full training.

## Future Roadmap

1. Verify that the moving hurdle actor is created correctly in the viewer.
2. Verify collision behavior with the robot.
3. Verify reset randomization for selected envs.
4. Add debug drawing only if the existing viewer tools are not enough.
5. Consider exposing dynamic obstacle state to privileged observations.
6. Add shifting gaps, changing step heights, and time-varying ramps.
7. Only after the scaffold is validated, run training comparisons.
