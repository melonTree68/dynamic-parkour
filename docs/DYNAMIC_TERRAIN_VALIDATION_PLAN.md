# Dynamic Terrain Validation Plan

This plan is for future validation after Isaac Gym is installed. It is not part of the current task to run these checks.

Current blocker: Isaac Gym was not found locally under `/home/shiyixiao`, and no Isaac Gym archive was found. Download Isaac Gym Preview 4 manually from NVIDIA Developer, extract it to `/home/shiyixiao/isaacgym` or `/home/shiyixiao/RobotProject/extreme-parkour/isaacgym`, then install from the extracted `python/` directory inside `.venv-parkour`.

Before running viewer checks, first confirm import-level setup:

```bash
source /home/shiyixiao/RobotProject/extreme-parkour/.venv-parkour/bin/activate
python -c "import isaacgym; print('isaacgym ok')"
python -c "from isaacgym import gymapi, gymtorch; print('gymapi/gymtorch ok')"
python -c "import legged_gym; print('legged_gym ok')"
python -c "import rsl_rl; print('rsl_rl ok')"
python -c "from legged_gym.utils.dynamic_obstacles import DynamicObstacleManager; print('DynamicObstacleManager ok')"
```

## 1. Tiny Viewer Check

Goal: confirm actor creation and visual motion.

Suggested constraints:

- Use a very small environment count, such as `num_envs = 1` or `num_envs = 4`.
- Set `dynamic_obstacles.enable = True`.
- Set `dynamic_obstacles.type = "moving_hurdle"`.
- Keep the original rewards, observations, and PPO code unchanged.
- Do not run training.

Expected result:

- One actor named `dynamic_hurdle` appears in each environment.
- The hurdle is placed at `env_origin + [base_position_x, base_position_y, base_position_z]`.
- The hurdle moves along the configured `motion_axis`.
- The static terrain mesh does not change.

## 2. Collision Check

Goal: verify that the moving hurdle can collide with the robot or a simple test object.

Suggested checks:

- Start with one environment and a slow hurdle frequency.
- Confirm the hurdle has a collision shape.
- Confirm `collision_enabled = True` produces contacts.
- Separately check `collision_enabled = False` before relying on the filter behavior.

Expected result:

- Contact behavior is visible and consistent with Isaac Gym collision groups/filters.
- No reward or observation logic is changed during this check.

## 3. Reset Randomization Check

Goal: verify selected environment resets update only selected obstacle parameters.

Suggested checks:

- Inspect `DynamicObstacleManager.get_state()` before and after `reset(env_ids)`.
- Confirm amplitude, frequency, and phase are resampled for reset envs.
- Confirm non-reset envs keep their current sampled parameters.
- Confirm z stays fixed for the MVP.

Expected result:

- `amplitude`, `frequency`, and `phase` change only for requested env ids when `randomize_on_reset = True`.
- `base_position` remains stable unless terrain origin changes through curriculum.

## 4. Static Baseline Check

Goal: verify `dynamic_obstacles.enable = False` preserves the original static Extreme Parkour behavior.

Suggested checks:

- Instantiate the baseline config with dynamic obstacles disabled.
- Confirm actor count remains one robot actor per environment.
- Confirm static terrain generation, goals, rewards, observations, and PPO code are unchanged.

Expected result:

- No dynamic obstacle actors are created.
- `LeggedRobot.root_states` behavior matches the original one-actor-per-env layout.

## 5. Future Training Check

Training is not part of this task.

Only after viewer, collision, reset, and static-baseline checks pass should future work consider:

- exposing dynamic obstacle state to privileged observations,
- adding shifting gaps / changing steps / time-varying ramps,
- running small-scale smoke training,
- then running full training comparisons.
