# Dynamic Terrain Design

## Objective

The original Extreme Parkour benchmark uses static heightfield/trimesh obstacles. This project extends it toward dynamic-obstacle parkour, including moving hurdles, shifting gaps, changing step heights, and time-varying ramps.

At this stage, the scope is terrain and obstacle generation only. No training experiments, evaluation runs, PPO changes, reward changes, or observation changes are included.

## Why Not Dynamically Modify Heightfields Or Meshes

Heightfields and triangle meshes are a good fit for static terrain generation. Dynamically editing them during simulation is more complex, more fragile, and likely to be slower than updating rigid actor states.

The first dynamic-obstacle version therefore keeps the original terrain mesh static and adds Isaac Gym actors. The MVP obstacle set uses box actors for moving hurdles, shifting gap boundaries, changing-height steps, and a pitch-varying ramp approximation.

## Primitive Layer

- `moving_hurdle`: a horizontally moving hurdle or box actor.
- `shifting_gap`: two thin box actors representing moving takeoff/landing boundaries. They move together so the apparent gap location shifts without editing the static mesh.
- `changing_step_height`: a fixed-size box actor whose center z position changes over time. This changes the effective top-surface height but does not resize the rigid body.
- `time_varying_ramp`: a box actor whose root orientation changes around the pitch axis. This is a conservative MVP approximation of a ramp, not a custom ramp mesh.

Unknown types raise `ValueError`. Unsupported actor-count requests raise clear `NotImplementedError` instead of falling back silently.

## Suite/Layout Layer

The primitive layer is now organized into original Extreme Parkour style task groups through `DYNAMIC_TERRAIN_SUITES` in `legged_gym/legged_gym/utils/dynamic_terrain_suites.py`.

Supported suites:

- `pure_hurdle`: four single-skill hurdle layouts.
- `pure_step`: four single-skill changing-step layouts.
- `pure_gap`: four single-skill shifting-gap layouts.
- `pure_ramp`: four single-skill pitch-varying ramp layouts.
- `mixed`: three layouts combining hurdle/step, gap/ramp, and all four primitive families.

`cfg.dynamic_obstacles.use_suites = False` by default, so existing primitive mode still uses `cfg.dynamic_obstacles.type`. When `use_suites = True`, the manager uses `suite`, `layout_id`, and `layout_randomization`. Layout randomization samples each environment layout at actor creation time; reset still resamples motion parameters, but does not swap actor assets.

This mirrors the intended training organization:

- Phase 1: train base policies separately on `pure_hurdle`, `pure_step`, `pure_gap`, and `pure_ramp`.
- Phase 2: later distill or combine policies using `mixed` or other multi-suite settings.

This stage only implements terrain/task organization. It does not run training or evaluation.

## MVP Scope

The current MVP implements all four proposal obstacle types and the suite/layout layer.

- `moving_hurdle`: one actor per environment, periodic motion along `x` or `y`.
- `shifting_gap`: two edge actors per environment, periodic motion along `x` or `y`.
- `changing_step_height`: one actor per environment, sinusoidal center-z motion.
- `time_varying_ramp`: one actor per environment, sinusoidal pitch motion.
- Randomized amplitude, frequency, and phase on reset.
- Disabled by default.
- Dynamic obstacle state is stored for future use but is not exposed to policy observations.

Motion rule:

```text
pos = base_pos + amplitude * sin(2*pi*frequency*t + phase)
```

The implementation stores a reset time per environment so motion can restart cleanly when selected envs reset. `get_state()` returns current position, velocity, orientation, angular velocity, sampled amplitude/frequency/phase, actor indices, and type-specific scalar state such as gap offset, step height, and ramp angle.

## Implementation

New file:

- `legged_gym/legged_gym/utils/dynamic_obstacles.py`
- `legged_gym/legged_gym/utils/dynamic_terrain_suites.py`

Key class:

- `DynamicObstacleManager`

Current methods:

- `create_assets()`
- `create_obstacles_for_env(env_handle, env_id, env_origin)`
- `bind_root_state_tensor(root_states)`
- `reset(env_ids, t)`
- `update(t)`
- `get_state()`

The manager creates box assets with `gym.create_box()`, creates the selected primitive or suite actor set per environment, stores actor indices, actor types, and layout ids, and updates the full Isaac Gym root-state tensor through `set_actor_root_state_tensor_indexed()`.

Config validation now rejects malformed motion ranges, negative frequencies, non-positive dimensions, invalid env ids, missing actor indices, and unsupported obstacle types before silently doing the wrong thing.

## Isaac Gym Assumptions

Dynamic actors use `AssetOptions.disable_gravity = True`. When `make_kinematic = True`, the scaffold also sets `AssetOptions.fix_base_link = True`, then updates the actor root state tensor directly. This should be validated in a small viewer run because Isaac Gym actor behavior may vary by Preview version.

Collision filtering uses the same-env actor creation path with collision filter `0` when `collision_enabled = True`. The `collision_enabled = False` path is a best-effort placeholder and should be validated before relying on it.

## Root-State Tensor Handling

Adding obstacle actors changes the actor root-state tensor from one actor per env to multiple actors per env. To avoid breaking the baseline robot code, `LeggedRobot` now keeps:

- `all_root_states`: the full actor root-state tensor.
- `root_states`: the existing robot-only view, `all_root_states.view(num_envs, actors_per_env, 13)[:, 0, :]`.
- `robot_actor_indices`: simulator-domain actor indices for robot reset calls.

With dynamic obstacles disabled, `actors_per_env == 1`, so behavior remains equivalent to the original baseline.

When dynamic actors are enabled, the scaffold expects the robot actor to be created first in every environment and dynamic obstacle actors after it. `LeggedRobot._init_buffers()` now checks this actor ordering against `robot_actor_indices`. If a future Isaac Gym version or new actor type changes ordering, the code raises a clear error instead of writing robot state into an obstacle row.

## Viewer/Debug Path

Use the lightweight script to inspect rendered dynamic actors without PPO:

```bash
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type moving_hurdle --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type shifting_gap --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type changing_step_height --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type time_varying_ramp --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --suite pure_hurdle --layout_id 0 --steps 500 --rows 2 --cols 2 --headless
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --suite mixed --layout_id 2 --steps 500 --rows 2 --cols 2
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --list_suites
```

Add `--headless` for an import/simulation smoke path without opening a viewer. The script forces `num_envs = 1`, uses a tiny terrain grid, steps zero actions, and does not create a PPO runner or wandb run.

On WSL, run the viewer from Windows Terminal rather than the VS Code terminal, keep `num_envs = 1`, and do not run full training just to inspect terrain.

## Future Extension Interface

Reserved obstacle class names remain present for a future per-obstacle implementation:

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
