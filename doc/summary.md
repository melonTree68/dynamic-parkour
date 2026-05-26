# Dynamic Terrain Final Summary

## Final Design Status

- Hurdles: thin barriers across the route, with suite layouts using mainly
  x-direction motion.
- Steps: actor-based changing-height approximation with z motion from a
  partially buried box.
- Gaps: simple stable boundary-shifting behavior with two platform actors.
- Ramps: actor ramps with tilt behavior; suite ramps emphasize forward-axis
  roll while pitch compatibility remains available.
- Dynamic obstacles remain disabled by default.

## Where To Look

- `legged_gym/legged_gym/utils/dynamic_obstacles.py`: runtime actor manager for
  dynamic obstacle creation, reset, update, and state tracking.
- `legged_gym/legged_gym/utils/dynamic_terrain_suites.py`: pure and mixed layout
  definitions plus tunable obstacle parameters.
- `legged_gym/legged_gym/envs/base/legged_robot_config.py`: base dynamic
  obstacle config; disabled by default.
- `legged_gym/legged_gym/envs/base/legged_robot.py`: environment integration.
- `legged_gym/legged_gym/scripts/view_dynamic_terrain.py`: lightweight
  viewer/debug entrypoint.
- `tools/plot_dynamic_terrain_layouts.py`: dynamic suite atlas generator.
- `tools/plot_original_terrain_atlas.py`: original static terrain atlas
  generator for comparison.
- `tools/check_terrain_design.py`: static checker for suite structure.
- `tune.md`: concise parameter tuning guide.

## Essential Commands

Generate the dynamic atlas:

```bash
python tools/plot_dynamic_terrain_layouts.py --out_dir terrain_layout_atlas
```

View one layout:

```bash
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --suite pure_gap --layout_id 0 --steps 50 --rows 2 --cols 2 --headless
```

Run the static checker:

```bash
python tools/check_terrain_design.py
```

## Tuning Parameters

In `dynamic_terrain_suites.py`:

- `base_position`: obstacle center `[x, y, z]`.
- `size`: actor box size `[x_length, y_width, z_height]`.
- `motion_axis`: motion direction or tilt axis, such as `x`, `y`, `z`, `roll`,
  or `pitch`.
- `amplitude_range`: motion amplitude range.
- `frequency_range`: motion frequency range.
- `phase_range`: phase range.
- `goals`: layout target/waypoint sequence.
- `corridor_half_width`: intended lateral corridor width.
- `runup_length` / `runout_length`: course spacing metadata.

Type-specific tuning:

- Hurdle: tune height, width, and x-motion amplitude/frequency.
- Step: tune height and z-motion amplitude/frequency.
- Gap: tune platform separation, gap size, and motion amplitude.
- Ramp: tune length, width, tilt axis, angle amplitude, frequency, and phase.

