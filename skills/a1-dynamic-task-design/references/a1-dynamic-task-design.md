## Static A1 Background

This section records the static `a1` construction path because `a1_dynamic` inherits from it and uses it as the main design reference. The current CLI default is `a1_dynamic`, but the static task remains the baseline for robot configuration, static obstacle semantics, and expert policies.

The static `a1` task is registered in [envs/__init__.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/__init__.py:44) as:

```python
task_registry.register("a1", LeggedRobot, A1ParkourCfg(), A1ParkourCfgPPO())
```

So `a1` does **not** use `A1RoughCfg`; it uses:

- Environment implementation: `LeggedRobot`
- Environment configuration: `A1ParkourCfg`
- Training configuration: `A1ParkourCfgPPO`

[train.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/scripts/train.py:71) passes `args.task` to [task_registry.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/task_registry.py:80), which instantiates `LeggedRobot(cfg=A1ParkourCfg(), ...)`.

## A1-Specific Configuration

[A1ParkourCfg](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/a1/a1_parkour_config.py:34) inherits almost everything from `LeggedRobotCfg`. It only specializes:

- Initial A1 pose: base height `0.42 m` and 12 default joint angles.
- PD controller: position control, stiffness `40`, damping `1`, action scale `0.25`, decimation `4`.
- Robot asset: `resources/robots/a1/urdf/a1.urdf`.
- Contact handling: penalize thigh/calf/base contact; terminate on base contact.
- Reward parameters: soft joint limit `0.9`, base height target `0.25`.
- PPO metadata: entropy coefficient and experiment name.

Thus, the robot model is A1-specific, but most parkour behavior is implemented in the shared base classes.

## Parkour Course Configuration

The actual default parkour task is defined in inherited [LeggedRobotCfg.terrain](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot_config.py:137):

- Terrain representation: triangle mesh.
- Curriculum enabled.
- Course tile size: `18 m x 4 m`.
- Curriculum grid: `10` difficulty rows x `40` terrain-type columns.
- Height sensing: enabled, producing `132` scan observations.
- Navigation goals per course: `8`.

The default terrain mixture is:

```python
"parkour":        0.2
"parkour_hurdle": 0.2
"parkour_flat":   0.2
"parkour_step":   0.2
"parkour_gap":    0.2
```

All ordinary rough-terrain families have weight zero.

## Terrain Generation

During `LeggedRobot` creation, [create_sim()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:551) constructs a [Terrain](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:43) object.

Because curriculum is enabled, `Terrain.curiculum()` creates one tile for each grid cell:

- Row `i` determines difficulty from `0` to `1`.
- Column `j` chooses the terrain family according to the configured proportions.

[Terrain.make_terrain()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:187) dispatches the five active families:

| Family           | Generator                                                                                           | Behavior                                            |
| ---------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `parkour`        | [parkour_terrain()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:509)        | Alternating raised/inclined stepping pads over pits |
| `parkour_hurdle` | [parkour_hurdle_terrain()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:700) | Repeated hurdles with lateral variation             |
| `parkour_flat`   | `parkour_hurdle_terrain(..., flat=True)`                                                            | Flat narrow route without raised hurdles            |
| `parkour_step`   | [parkour_step_terrain()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:783)   | Ascending then descending blocks                    |
| `parkour_gap`    | [parkour_gap_terrain()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:614)    | Traversable corridor interrupted by gaps            |

Each generator writes:

- A height field for the tile.
- Eight waypoint goals in `terrain.goals`.

The complete height field is converted to an Isaac Gym triangle mesh, with an edge mask used for penalizing foot placement near obstacle boundaries.

## Robot Placement And Goal Following

[LeggedRobot._create_envs()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:1233) loads the A1 URDF and creates thousands of robot instances.

[_get_env_origins()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:1425) assigns each environment:

- A terrain tile.
- An initial curriculum level.
- A terrain-class ID.
- Its sequence of eight waypoint goals.

At every step, [_update_goals()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:256) advances the current goal when the robot remains within `0.2 m` of it for `0.1 s`. The target waypoint determines the desired heading and progress direction.

## Observations

[compute_observations()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:458) builds observations from:

- Angular velocity and roll/pitch.
- Current and next goal yaw offsets.
- Commanded forward velocity.
- Terrain-class indicators.
- Joint positions, velocities, prior actions, and foot contacts.
- Local height scan samples.
- Domain-randomization privileged information.
- Ten-step proprioceptive history.

The policy therefore learns obstacle traversal primarily through terrain height scans or, during distillation, optional camera depth input.

## Rewards, Failure, And Curriculum

Reward scales come from [LeggedRobotCfg.rewards](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot_config.py:329). Important parkour terms include:

- Progress velocity toward the current goal.
- Heading alignment with the goal.
- Penalties for vertical/angular motion, collisions, torque/action changes, posture error, foot stumbling, and foot placement on edges.

The implementations are in [legged_robot.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:1786).

Episodes terminate when the robot:

- Reaches the last goal.
- Exceeds episode time.
- Falls below height `-0.25`.
- Rolls or pitches beyond `1.5 rad`.

After reset, [_update_terrain_curriculum()](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py:866) moves the robot to harder or easier terrain rows based on distance traveled.

## Where The Dynamic Task Fits

For a parkour task using the same A1 robot and shared logic, the normal structure is:

1. Add a new config class beside [a1_parkour_config.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/a1/a1_parkour_config.py:34), subclassing `LeggedRobotCfg` and overriding `terrain`, rewards, commands, or robot settings.
2. Add its PPO config class.
3. Import and register it under a new task name in [envs/__init__.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/__init__.py:44).
4. If it needs a new obstacle family, implement a generator in [terrain.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:187) and add corresponding dispatch logic in `make_terrain()`.
5. Consider updating [play.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/scripts/play.py:67) and [evaluate.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/scripts/evaluate.py:74), because both currently overwrite the registered task's terrain distribution during testing.

A subtle constraint: `terrain_dict` is converted to an ordered list of proportions, and `make_terrain()` interprets entries by fixed positional ranges. Adding a terrain name to the dictionary alone will not construct it; the ordered dispatcher must be changed consistently.

## Dynamic A1 Parkour Task

`a1_dynamic` is a separate task that keeps the A1 robot, PPO inheritance, goal-following interface, curriculum shape, and observation dimensions from `a1`, while replacing the static parkour course families with scripted moving obstacle actors.

Registration is in [envs/__init__.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/__init__.py):

```python
task_registry.register(
    "a1_dynamic", DynamicLeggedRobot, A1DynamicParkourCfg(), A1DynamicParkourCfgPPO()
)
```

The main files are:

- [a1_dynamic_config.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/a1/a1_dynamic_config.py): user-facing dynamic task config.
- [a1_dynamic.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/a1/a1_dynamic.py): scripted actor creation, reset sampling, per-substep motion, dynamic goals, dynamic height scan overlay, and the placeholder takeoff penalty.
- [terrain.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py): static heightfield foundations, dynamic-family dispatch, and per-tile dynamic metadata.
- [legged_robot.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/base/legged_robot.py): shared hooks and multi-actor root-state support used by dynamic tasks while preserving one-actor behavior for `a1`.

`A1DynamicParkourCfg` inherits from `A1ParkourCfg`, uses `env.num_envs = 2048`, keeps the 10-row curriculum, eight-goal course format, 132-point terrain scan, and unchanged policy observation shape. Static terrain families are weighted zero; the active dynamic families are currently:

```python
"dynamic_hurdle": 0.2
"dynamic_gap": 0.2
"dynamic_tilted_pads": 0.2
"dynamic_step": 0.2
"dynamic_demo": 0.2
```

`dynamic_demo` is the dynamic analogue of `demo_terrain()`: moving hurdle, moving step, translating gap takeoff/landing pair, and two tilting pads.

## Dynamic Terrain Metadata

Dynamic terrain generators do not bake moving obstacles into the triangle mesh. They create static foundations and store metadata that `DynamicLeggedRobot` turns into scripted obstacle actors.

The per-tile metadata is allocated in `Terrain.__init__`:

- `dynamic_family[row, col]`: family ID, such as hurdle, gap, tilted pads, step, or demo.
- `dynamic_difficulty[row, col]`: generated curriculum difficulty.
- `dynamic_obstacle_specs[row, col, group, slot, 7]`: actor spec `[x, y, z, sx, sy, sz, extra]`.
- `dynamic_motion_types[row, col, group, slot]`: motion type for each slot.
- `dynamic_motion_groups[row, col, group, slot]`: signal group, so paired slots can share one motion.
- `dynamic_goal_groups[row, col, goal]`: motion group used to translate moving goals.
- `dynamic_goal_mask`: retained to mark goals associated with moving support.

There are six obstacle groups per tile and two actor slots per group. `DynamicLeggedRobot` therefore creates twelve additional actors per environment. Gap groups use both slots for takeoff and landing support; hurdle, tilted pad, and step groups use one active slot and park the unused slot below the course.

`dynamic_obstacle_specs[..., 6]` is currently used as type-specific extra metadata. For tilted pads it stores a fixed roll sign: `+1` for left-tilting pads and `-1` for right-tilting pads. Pure `dynamic_tilted_pads` alternates signs across the six pads; `dynamic_demo` assigns opposite signs to its two pads.

## Dynamic Runtime

`DynamicLeggedRobot` inherits shared A1 parkour behavior and adds scripted obstacle actors:

- `_prepare_additional_assets()` creates gravity-disabled box assets for inactive placeholders, hurdles, gap platforms, tilted pads, and step columns.
- `_create_additional_actors()` creates the twelve dynamic actor slots after the robot actor.
- `_reset_additional_actors()` gathers the current tile metadata after reset or curriculum reassignment and samples motion amplitude, period, and phase.
- `_pre_physics_step()` advances dynamic time and applies scripted transforms every physics substep.
- `_apply_dynamic_poses()` writes actor poses and analytic velocities into the actor root-state tensor.
- `_update_dynamic_goals()` translates goals whose support surface translates.
- `_get_heights()` starts from the inherited static heightmap samples, then analytically overlays current dynamic obstacle top surfaces. Observation shape and scan count stay unchanged.

The base class keeps `root_states` as the robot actor view and stores the full actor-root tensor separately. Resets and pushes use robot actor indices so the extra obstacle actors do not change `a1` semantics.

The dynamic reward scale `bad_dynamic_takeoff = -1.0` is configured, but `_reward_bad_dynamic_takeoff()` intentionally returns a zero tensor. It is a logging and future-extension hook for dynamic hurdle/gap takeoff quality.

## Dynamic Tuning Map

Tune these values in `A1DynamicParkourCfg.dynamic_obstacles` in [a1_dynamic_config.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/a1/a1_dynamic_config.py). Values that are pairs are linearly interpolated from easiest difficulty `0` to hardest difficulty `1`.

- `num_obstacles = 6`, `slots_per_obstacle = 2`: fixed actor layout, matching six crossings with two slots each.
- `inactive_z`: parking height for inactive actor slots.
- Hurdles:
  - `hurdle_thickness`: physical x-axis thickness.
  - `hurdle_width`: y-axis width.
  - `hurdle_height_min`, `hurdle_height_max`: difficulty-interpolated uniform sampling bounds for each hurdle height.
  - `hurdle_spacing`: sampled x spacing between hurdle crossings.
  - `hurdle_amplitude`, `hurdle_period_min`, `hurdle_period_max`: x-translation amplitude and period ranges.
- Gaps:
  - `gap_size`: difficulty-interpolated intended gap length.
  - `gap_platform_dims = [x_len, y_width, z_thickness]`: box dimensions for each moving takeoff or landing platform actor.
  - `gap_spacing`: sampled x spacing between intended gaps.
  - `gap_amplitude`, `gap_period_min`, `gap_period_max`: x-translation amplitude and period ranges. Pure `dynamic_gap` tiles synchronize all six gaps to avoid unintended extra openings between consecutive gaps.
- Tilted pads:
  - `tilted_pad_dims = [x_len, y_width, z_thickness]`: pad actor dimensions.
  - `tilted_pad_spacing`: sampled x spacing between pads.
  - `tilted_pad_y_range_coeff`: multiplies `terrain.y_range` before sampling tilted-pad lateral offsets.
  - `tilted_pad_amplitude`, `tilted_pad_period_min`, `tilted_pad_period_max`: roll amplitude and period ranges.
  - `tilted_pad_min_roll_fraction`: lower fraction of sampled roll amplitude used by the sinusoidal absolute-roll oscillation.
- Steps:
  - `step_dims = [x_len, y_width]`: step actor horizontal dimensions.
  - `step_height_min`, `step_height_max`: difficulty-interpolated uniform bounds for each height transition.
  - `step_spacing`: sampled x spacing between steps.
  - `step_amplitude`, `step_period_min`, `step_period_max`: z-translation amplitude and period ranges.
- All dynamic obstacle types:
  - `amplitude_min_fraction`: actual amplitude is sampled as `max_amplitude * Uniform(amplitude_min_fraction, 1.0)`. This is currently `0.8`.
- Mixed demo:
  - `dynamic_demo_spacing`: five spacing pairs for the mixed course sequence: start to hurdle, hurdle to step, step to gap, gap to tilted pad 1, and tilted pad 1 to tilted pad 2.

Smaller periods mean faster motion. `dynamic_demo` uses each obstacle's own type-specific amplitude and period settings.

## Static A1 Counterparts

`a1` has no `dynamic_obstacles` group. Comparable values live in `Terrain.make_terrain()` dispatch and the static generator functions in [terrain.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py).

- Obstacle count: dynamic `num_obstacles = 6` corresponds to `a1`'s `num_goals - 2` crossings.
- Lateral offsets: `a1` generators independently sample each crossing's y offset from `terrain.y_range`; `a1_dynamic` follows the same independent, non-cumulative convention.
- Hurdle counterpart:
  - Static thickness is `stone_len = 0.1 + 0.3 * difficulty`.
  - Static height range is `[0.1 + 0.1 * difficulty, 0.15 + 0.25 * difficulty]`, equivalent to easy `[0.10, 0.15]` and hard `[0.20, 0.40]`.
  - Static x spacing uses `[1.2, 2.2]`.
- Gap counterpart:
  - Static gap size is `0.1 + 0.7 * difficulty`, equivalent to `[0.10, 0.80]`.
  - Static x advance includes `gap_size + Uniform(0.8, 1.5)`.
  - There is no static actor counterpart for `gap_platform_dims`; it is a dynamic-only moving support box size.
- Tilted-pad/ramp counterpart:
  - Static parkour pads use `stone_len = [0.9 - 0.3*d, 1.0 - 0.2*d]`, `stone_width = 1.0`, and x spacing `[-0.1, 0.1 + 0.3*d]`.
  - Static incline height is `0.25 * difficulty`, so the regular ramp roll magnitude is `atan(2 * 0.25 * d / 1.0) = atan(0.5*d)`. At difficulty `1`, this is about `0.46365 rad` or `26.57 deg`.
  - The final static ramp uses `last_incline_height = 0.1 + 0.15*d`, giving roll `atan(0.2 + 0.3*d)`.
- Step counterpart:
  - Static step height is deterministic: `0.1 + 0.35 * difficulty`.
  - Static x range is `[0.3, 1.5]`, with effective section length including the sampled step height in the current generator.

## Current Dynamic Generator Decisions

- `dynamic_hurdle_terrain()` samples hurdle heights independently, stores the configured x thickness, and places waypoints near each crossing's sampled lateral center.
- `dynamic_gap_terrain()` builds lowered slices only around intended openings and uses synchronized translation for all six gaps in a pure gap tile. The gap length is constant over time because takeoff and landing supports translate together.
- `dynamic_tilted_pads_terrain()` creates a pit foundation and alternating-sign pads. The roll sign is fixed by pad index, while the roll magnitude varies over time.
- `dynamic_step_terrain()` samples per-transition increments and accumulates an up/down progression. Step actors are tall buried columns; placing them by top surface ensures the bottom remains at or below ground through the motion range.
- `dynamic_demo_terrain()` emits eight goals: start, hurdle, step, gap takeoff, gap landing, pad 1, pad 2, finish.

Dynamic tilted pads mirror the static `parkour_terrain()` ramp convention: the lateral offset sign is coupled to the roll sign. Positive roll has the lower side at smaller y and is shifted toward positive y; negative roll has the lower side at larger y and is shifted toward negative y. Goals use the same shifted lateral center as the pad.

Tilted pad runtime uses fixed sign and positive magnitude:

```python
absolute_roll = amplitude * (
    tilted_pad_min_roll_fraction
    + (1.0 - tilted_pad_min_roll_fraction) * (sin(phase) + 1.0) / 2
)
roll = roll_sign * absolute_roll
```

Thus one pad always tilts left, the next always right, and the absolute roll oscillates between `tilted_pad_min_roll_fraction * sampled_amplitude` and `sampled_amplitude`.

## Validation Notes

Use the project `parkour` conda environment for Python checks. If Isaac Gym cannot find `libpython3.8.so.1.0`, set `LD_LIBRARY_PATH=/home/zhijie/apps/miniconda3/envs/parkour/lib`.

Useful validation targets after changing this subsystem:

- Registration/config: `a1_dynamic` resolves to `DynamicLeggedRobot` and `A1DynamicParkourCfg`; `a1` still resolves to the existing `LeggedRobot` and `A1ParkourCfg`.
- Terrain tests: dynamic families generate eight goals, dynamic metadata, correct family IDs, lateral offsets within `terrain.y_range`, and expected spacing/height ranges.
- Gap tests: pure dynamic gap tiles have six intended constant-length gaps, shared translation, and no extra unsupported openings between consecutive gaps.
- Tilted pad tests: pure tilted pads alternate fixed roll signs; `dynamic_demo`'s two pads have opposite signs; absolute roll stays within `[tilted_pad_min_roll_fraction * amplitude, amplitude]`.
- Step tests: step progression remains up/down, and every step column bottom stays at or below ground over its full z-motion range.
- Goal/scan tests: only gap-related goals translate; height scans overlay current dynamic obstacle surfaces while preserving `(num_envs, 753)` observations and 132 height samples.
- Reward tests: `bad_dynamic_takeoff` is present in episode reward bookkeeping and contributes exactly zero.
- Runtime smoke: reduced-environment Isaac Gym stepping for both `a1_dynamic` and `a1`, with finite observations/rewards and valid reset/curriculum reassignment.
