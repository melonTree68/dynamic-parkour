# Terrain Code Map

## Terrain Class

The `Terrain` class is defined in `legged_gym/legged_gym/utils/terrain.py`.

`LeggedRobot.create_sim()` in `legged_gym/legged_gym/envs/base/legged_robot.py` creates `Terrain(self.cfg.terrain, self.num_envs)` when `cfg.terrain.mesh_type` is `heightfield` or `trimesh`.

## Heightfield Creation

`Terrain.__init__()` allocates `height_field_raw` as one large `np.int16` grid covering all terrain rows and columns plus a border. Each sub-terrain is generated into an Isaac Gym `terrain_utils.SubTerrain`, then copied into the global map by `Terrain.add_terrain_to_map()`.

For `mesh_type == "heightfield"`, `_create_heightfield()` passes the flattened height samples to `gym.add_heightfield()`.

For `mesh_type == "trimesh"`, `Terrain.__init__()` converts the heightfield with either `convert_heightfield_to_trimesh()` or `convert_heightfield_to_trimesh_delatin()`, then `_create_trimesh()` passes vertices and triangles to `gym.add_triangle_mesh()`.

## Terrain Type Selection

`LeggedRobotCfg.terrain.terrain_dict` defines named terrain probabilities. `terrain_proportions` is normalized in `Terrain.__init__()`.

`Terrain.curiculum()` iterates over terrain rows and columns. A row controls difficulty, while a column controls the terrain choice. With `random=True`, difficulty is sampled randomly. The terrain choice is dispatched by `Terrain.make_terrain()` using cumulative proportions.

`Terrain.selected_terrain()` can generate one explicit terrain type from `cfg.terrain.terrain_kwargs`, but the default path uses the curriculum/randomized dispatch.

## Parkour Terrain Functions

- `parkour_terrain()`: creates a sequence of alternating angled stones over a pit-like low area, records goal centers, and pads map edges.
- `parkour_hurdle_terrain()`: creates static heightfield hurdles at sampled x/y offsets, optionally flattened for `parkour_flat`, and records intermediate goals.
- `parkour_gap_terrain()`: creates static gaps by lowering sections of the heightfield and preserving a valid corridor around sampled y offsets.
- `parkour_step_terrain()`: creates step-up and step-down static heightfield regions with a valid corridor.
- `gap_parkour_terrain()`: creates a central gap-style static obstacle for the older `gaps` terrain entry.
- `demo_terrain()`: composes hurdle, step, gap, and parkour-like elements for demonstration terrain.
- `add_roughness()` adds random height noise to many terrain variants after the main structure is generated.

`parkour_flat` currently reuses `parkour_hurdle_terrain(..., flat=True)`, so the goal/corridor pattern remains but hurdle heightfield blocks are not raised.

## Goals

Each parkour terrain function creates a local `goals` array in terrain-grid coordinates and stores it as `terrain.goals` in meters.

`Terrain.add_terrain_to_map()` offsets these local goals by the sub-terrain row and column and writes them into `self.goals[row, col]`.

`LeggedRobot._get_env_origins()` converts `self.terrain.goals` to `self.terrain_goals`, selects goals by `terrain_levels` and `terrain_types`, and stores per-env goals in `self.env_goals`. `self.cur_goals` and `self.next_goals` are gathered by `_gather_cur_goals()`.

`LeggedRobot._update_goals()` updates goal progress, target vectors, and target yaw from the robot root state.

## Terrain Mesh Insertion

The static terrain is added to the Isaac Gym simulation in:

- `LeggedRobot._create_ground_plane()`
- `LeggedRobot._create_heightfield()`
- `LeggedRobot._create_trimesh()`

The project default uses `mesh_type = "trimesh"`, so `_create_trimesh()` is the main static parkour path.

## Environment Origins

`Terrain.add_terrain_to_map()` computes `env_origins[row, col]` for terrain origins.

`LeggedRobot._get_env_origins()` maps these terrain origins to per-environment `self.env_origins`. With heightfields/trimeshes, `self.custom_origins = True`; otherwise a regular grid is used.

## Robot Actor Creation

The robot asset is loaded and robot actors are created in `LeggedRobot._create_envs()`.

The key call is:

```python
self.gym.create_actor(env_handle, robot_asset, start_pose, "anymal", i, self.cfg.asset.self_collisions, 0)
```

## Best Hooks For Additional Obstacle Actors

The best creation hook is `LeggedRobot._create_envs()`, after the robot actor is created for each env and before cameras are attached. The dynamic scaffold now uses `DynamicObstacleManager.create_assets()` once and `create_obstacles_for_env()` inside the environment loop.

The static terrain mesh should not be modified for dynamic actors.

Dynamic obstacle `base_position_x/y/z` values are local offsets from `self.env_origins[i]`. This keeps dynamic actor placement tied to the same origin system used for robot starts and parkour goals.

## Best Hooks For Per-Step Dynamic Updates

Use `LeggedRobot.step()` before the decimated physics loop so actor root states are updated before simulation advances. The scaffold calls `self.dynamic_obstacles.update(self.common_step_counter * self.dt)` there.

For future lower-level physics-rate updates, the same manager could be called inside the decimation loop with substep time.

The manager writes only dynamic actor rows in the full actor root-state tensor. `LeggedRobot.root_states` remains the robot-only view used by reward, reset, and observation code.

## Best Hooks For Reset Randomization

Use `LeggedRobot.reset_idx()`, after robot root state reset and command resampling. The scaffold calls `self.dynamic_obstacles.reset(env_ids, self.common_step_counter * self.dt)` there.

This keeps dynamic obstacle randomization separate from robot DOF/root reset logic.

## Parts To Avoid Modifying

- PPO and `rsl_rl` training code.
- Policy network definitions.
- Reward functions and reward scales.
- Observation layout and privileged observation layout.
- Existing heightfield/trimesh generation behavior.
- Terrain proportions and task defaults, unless a future experiment explicitly changes them.
- Training, play, or eval scripts beyond documentation or tiny metadata hooks.
