# Dynamic Terrain Design

## Objective

The original Extreme Parkour benchmark uses static heightfield/trimesh obstacles. This project extends it toward dynamic-obstacle parkour, including moving hurdles, shifting gaps, changing step heights, and time-varying ramps.

At this stage, the scope is terrain and obstacle generation only. No training experiments, evaluation runs, PPO changes, reward changes, or observation changes are included.

## Why Not Dynamically Modify Heightfields Or Meshes

Heightfields and triangle meshes are a good fit for static terrain generation. Dynamically editing them during simulation is more complex, more fragile, and likely to be slower than updating rigid actor states.

The first dynamic-obstacle version therefore keeps the original terrain mesh static and adds Isaac Gym actors. The MVP uses a box actor for a moving hurdle.

## Planned Dynamic Obstacle Types

- `moving_hurdle`: a horizontally moving hurdle or box actor.
- `shifting_gap`: planned representation using moving platforms or moving takeoff/landing boundaries.
- `changing_step_height`: planned box actor whose z position or effective height changes over time.
- `time_varying_ramp`: planned tilted rigid body or multi-box approximation.

Unimplemented types raise clear errors instead of falling back silently.

## MVP Scope

The current MVP implements only `moving_hurdle`.

- One hurdle actor per environment.
- Periodic motion along `x` or `y`.
- Randomized amplitude, frequency, and phase on reset.
- Fixed z position.
- Disabled by default.
- Dynamic obstacle state is stored for future use but is not exposed to policy observations.

Motion rule:

```text
pos = base_pos + amplitude * sin(2*pi*frequency*t + phase)
```

The implementation stores a reset time per environment so the motion can restart cleanly when selected envs reset.

## Implementation

New file:

- `legged_gym/legged_gym/utils/dynamic_obstacles.py`

Key class:

- `DynamicObstacleManager`

Current methods:

- `create_assets()`
- `create_obstacles_for_env(env_handle, env_id, env_origin)`
- `bind_root_state_tensor(root_states)`
- `reset(env_ids, t)`
- `update(t)`
- `get_state()`

The manager creates a box asset with `gym.create_box()`, creates one actor named `dynamic_hurdle` per environment, stores actor indices, and updates the full Isaac Gym root-state tensor through `set_actor_root_state_tensor_indexed()`.

Config validation now rejects malformed motion ranges, negative frequencies, non-positive hurdle dimensions, invalid env ids, missing actor indices, and unsupported obstacle types before silently doing the wrong thing.

## Isaac Gym Assumptions

The moving hurdle uses `AssetOptions.disable_gravity = True`. When `make_kinematic = True`, the scaffold also sets `AssetOptions.fix_base_link = True`, then updates the actor root state tensor directly. This should be validated in a small viewer run because Isaac Gym actor behavior may vary by Preview version.

Collision filtering uses the same-env actor creation path with collision filter `0` when `collision_enabled = True`. The `collision_enabled = False` path is a best-effort placeholder and should be validated before relying on it.

## Root-State Tensor Handling

Adding obstacle actors changes the actor root-state tensor from one actor per env to multiple actors per env. To avoid breaking the baseline robot code, `LeggedRobot` now keeps:

- `all_root_states`: the full actor root-state tensor.
- `root_states`: the existing robot-only view, `all_root_states.view(num_envs, actors_per_env, 13)[:, 0, :]`.
- `robot_actor_indices`: simulator-domain actor indices for robot reset calls.

With dynamic obstacles disabled, `actors_per_env == 1`, so behavior remains equivalent to the original baseline.

When dynamic actors are enabled, the scaffold expects the robot actor to be created first in every environment and the dynamic hurdle actor second. `LeggedRobot._init_buffers()` now checks this actor ordering against `robot_actor_indices`. If a future Isaac Gym version or new actor type changes ordering, the code raises a clear error instead of writing robot state into an obstacle row.

## Future Extension Interface

Reserved obstacle names are present for future work:

- `MovingHurdleObstacle`
- `ShiftingGapObstacle`
- `ChangingStepObstacle`
- `TimeVaryingRampObstacle`

Future obstacle classes should support:

- `create`
- `reset`
- `update`
- `get_state`

Obstacle state can later be exposed to privileged observations, but this stage intentionally does not change observations.
