# Dynamic Terrain Usage

## Current Implementation

The repository now contains actor-based dynamic terrain MVPs for:

- `moving_hurdle`
- `shifting_gap`
- `changing_step_height`
- `time_varying_ramp`

- Dynamic obstacles are disabled by default.
- The original terrain heightfield/trimesh remains static.
- No reward changes.
- No observation changes.
- No policy or PPO changes.
- No training or experiments were run in this stage.

## Enabling The MVP

In a config derived from `LeggedRobotCfg`, enable:

```python
env_cfg.dynamic_obstacles.enable = True
env_cfg.dynamic_obstacles.type = "moving_hurdle"
```

Replace `"moving_hurdle"` with `"shifting_gap"`, `"changing_step_height"`, or `"time_varying_ramp"` to inspect the other MVPs. Do this only for a small viewer/debug run at first.

## Configuration Fields

- `enable`: global switch. Default is `False`.
- `type`: obstacle type. Supported values are `"moving_hurdle"`, `"shifting_gap"`, `"changing_step_height"`, and `"time_varying_ramp"`.
- `num_obstacles_per_env`: legacy/common guard. The manager derives the actual actor count from the selected type; `shifting_gap` uses two edge actors.
- `debug_draw`: reserved for future visualization helpers.
- `randomize_on_reset`: resample motion parameters for reset envs.
- `asset_density`: density passed to Isaac Gym asset options for dynamic actors.
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
- `gap_edge_length`: shifting-gap edge box length along x.
- `gap_edge_width`: shifting-gap edge box width along y.
- `gap_edge_height`: shifting-gap edge box height along z.
- `gap_edge_separation`: distance between the two edge actor centers.
- `gap_base_position_x/y/z`: center offset for the pair of shifting-gap edges.
- `gap_motion_axis`: `"x"` or `"y"`.
- `gap_amplitude_range`, `gap_frequency_range`, `gap_phase_range`: shifting-gap motion sampling ranges.
- `step_length`, `step_width`, `step_height`: changing-step box dimensions.
- `step_base_position_x/y/z`: changing-step base center position.
- `step_height_amplitude_range`, `step_frequency_range`, `step_phase_range`: changing-step z-motion sampling ranges.
- `ramp_length`, `ramp_width`, `ramp_thickness`: time-varying ramp box dimensions.
- `ramp_base_position_x/y/z`: ramp base center position.
- `ramp_base_pitch`: baseline pitch angle in radians.
- `ramp_pitch_amplitude_range`, `ramp_frequency_range`, `ramp_phase_range`: ramp pitch-motion sampling ranges.
- `make_kinematic`: sets a fixed-base, gravity-disabled box scaffold and updates root state manually.
- `collision_enabled`: best-effort collision filter switch for future validation.

The base position is interpreted in local environment coordinates and then offset by `env_origin`. The default `base_position_x = 2.0` places the hurdle shortly after the robot start area without changing static parkour goals or terrain generation.

Invalid obstacle types, invalid motion axes, malformed ranges, negative frequencies, and non-positive dimensions raise errors instead of silently falling back.

## Viewer Check

Use the viewer/debug script to render one environment without training:

```bash
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type moving_hurdle --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type shifting_gap --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type changing_step_height --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type time_varying_ramp --steps 1000
```

For a headless smoke path:

```bash
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type moving_hurdle --steps 100 --headless
```

The script:

- imports Isaac Gym before torch,
- forces `num_envs = 1`,
- uses a tiny terrain grid by default,
- enables only the selected dynamic obstacle,
- steps zero actions,
- does not create a PPO runner,
- does not use wandb.

Confirm:

- The selected actor appears.
- The actor moves or rotates along the configured motion.
- Collision behavior matches expectations.
- Reset randomization changes amplitude, frequency, or phase.

On WSL, run from Windows Terminal rather than the VS Code terminal, keep `num_envs = 1`, and do not run full training just to inspect terrain.

## Future Roadmap

1. Verify each obstacle actor type in the viewer.
2. Verify collision behavior with the robot.
3. Verify reset randomization for selected envs.
4. Add debug drawing only if the existing viewer tools are not enough.
5. Consider exposing dynamic obstacle state to privileged observations.
6. Only after the scaffold is validated, run training comparisons.
