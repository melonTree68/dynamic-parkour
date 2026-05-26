## Construction Path

The default CLI task is `a1`, because `--task` defaults to `"a1"` in [helpers.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/helpers.py:201).

At import time, [envs/__init__.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/__init__.py:44) registers it as:

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

## Where A New Task Fits

For another parkour task using the same A1 robot and shared logic, the normal structure is:

1. Add a new config class beside [a1_parkour_config.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/a1/a1_parkour_config.py:34), subclassing `LeggedRobotCfg` and overriding `terrain`, rewards, commands, or robot settings.
2. Add its PPO config class.
3. Import and register it under a new task name in [envs/__init__.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/envs/__init__.py:44).
4. If it needs a new obstacle family, implement a generator in [terrain.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/utils/terrain.py:187) and add corresponding dispatch logic in `make_terrain()`.
5. Consider updating [play.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/scripts/play.py:67) and [evaluate.py](/home/zhijie/extreme-parkour/legged_gym/legged_gym/scripts/evaluate.py:74), because both currently overwrite the registered task's terrain distribution during testing.

A subtle constraint: `terrain_dict` is converted to an ordered list of proportions, and `make_terrain()` interprets entries by fixed positional ranges. Adding a terrain name to the dictionary alone will not construct it; the ordered dispatcher must be changed consistently.
