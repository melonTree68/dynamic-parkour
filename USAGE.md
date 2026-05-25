# Terrain Design Summary

## What We Implemented

We extended the original Extreme Parkour terrain system with an actor-based dynamic terrain design.

The original static terrain pipeline is preserved. Dynamic obstacles are added as Isaac Gym actors instead of modifying heightfields or triangle meshes. This keeps the original baseline unchanged unless dynamic obstacles are explicitly enabled.

The terrain design now has two layers:

### 1. Dynamic Obstacle Primitives

The following dynamic obstacle primitives were implemented:

- `moving_hurdle`
- `shifting_gap`
- `changing_step_height`
- `time_varying_ramp`

These primitives are managed by `DynamicObstacleManager`, which handles actor creation, reset, update, and state tracking.

### 2. Dynamic Terrain Task Suites

The primitive obstacles were organized into task-oriented terrain suites:

- `pure_hurdle`
- `pure_step`
- `pure_gap`
- `pure_ramp`
- `mixed`

Each pure suite contains multiple layouts for single-skill training. The mixed suite contains combined layouts for future multi-skill or distillation experiments.

This structure follows the intended training organization:

- Stage 1: train base policies on pure obstacle tasks.
- Stage 2: combine or distill multiple skills using mixed terrain layouts.

## Where to Look

### Dynamic obstacle manager

```text
legged_gym/legged_gym/utils/dynamic_obstacles.py
```

This file contains the implementation of dynamic obstacle actor creation, reset, update, and state management.

### Dynamic terrain suite definitions

```text
legged_gym/legged_gym/utils/dynamic_terrain_suites.py
```

This file defines the pure hurdle, pure step, pure gap, pure ramp, and mixed terrain layouts.

### Base configuration

```text
legged_gym/legged_gym/envs/base/legged_robot_config.py
```

This file contains the dynamic obstacle configuration. Dynamic obstacles remain disabled by default.

### Environment integration

```text
legged_gym/legged_gym/envs/base/legged_robot.py
```

This file integrates dynamic obstacles into environment creation, reset, and simulation update.

### Dynamic A1 task entries

```text
legged_gym/legged_gym/envs/a1/
legged_gym/legged_gym/envs/__init__.py
```

These files contain or register the dynamic A1 task variants:

- `a1_dynamic_hurdle`
- `a1_dynamic_step`
- `a1_dynamic_gap`
- `a1_dynamic_ramp`
- `a1_dynamic_mixed`

### Visualization debug entrypoint

```text
legged_gym/legged_gym/scripts/view_dynamic_terrain.py
```

This script is used to inspect primitive or suite-based dynamic terrain layouts without running PPO training.

### Terrain design checker

```text
tools/check_terrain_design.py
```

This checker validates the structure of the dynamic terrain design.
