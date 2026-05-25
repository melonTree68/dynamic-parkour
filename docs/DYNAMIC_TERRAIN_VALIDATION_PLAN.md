# Dynamic Terrain Validation Plan

This plan is for future validation after Isaac Gym is installed. It is not part of the current task to run these checks.

Current setup note: use the prepared `parkour38` conda environment for local checks. If Isaac Gym is missing, download Isaac Gym Preview 4 manually from NVIDIA Developer, extract it to `/home/shiyixiao/isaacgym` or `/home/shiyixiao/RobotProject/extreme-parkour/isaacgym`, then install from the extracted `python/` directory inside the active environment.

Before running viewer checks, first confirm import-level setup:

```bash
conda activate parkour38
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
- For primitive checks, set `dynamic_obstacles.use_suites = False` and `dynamic_obstacles.type` to one of:
  - `"moving_hurdle"`
  - `"shifting_gap"`
  - `"changing_step_height"`
  - `"time_varying_ramp"`
- For suite checks, set `dynamic_obstacles.use_suites = True` and `dynamic_obstacles.suite` to one of:
  - `"pure_hurdle"`
  - `"pure_step"`
  - `"pure_gap"`
  - `"pure_ramp"`
  - `"mixed"`
- Keep the original rewards, observations, and PPO code unchanged.
- Do not run training.

Preferred command path:

```bash
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type moving_hurdle --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type shifting_gap --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type changing_step_height --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --obstacle_type time_varying_ramp --steps 1000
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --suite pure_hurdle --layout_id 0 --steps 500 --rows 2 --cols 2 --headless
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --task a1 --suite mixed --layout_id 2 --steps 500 --rows 2 --cols 2
python legged_gym/legged_gym/scripts/view_dynamic_terrain.py --list_suites
```

For WSL, run from Windows Terminal rather than the VS Code terminal, keep `num_envs = 1`, and do not run full training just to inspect terrain.

Expected result:

- The selected dynamic actor set appears in the environment.
- For `moving_hurdle`, the hurdle is placed at `env_origin + [base_position_x, base_position_y, base_position_z]` and moves along the configured `motion_axis`.
- For `shifting_gap`, two thin edge actors appear and move together along `gap_motion_axis`.
- For `changing_step_height`, one step actor appears and moves along z.
- For `time_varying_ramp`, one ramp box appears and changes pitch angle over time.
- The static terrain mesh does not change.
- For suite mode, `get_state()` includes `suite`, `layout_id`, `actor_indices`, `actor_types`, current positions/orientations, and type-specific state.

## 2. Collision Check

Goal: verify that the moving hurdle can collide with the robot or a simple test object.

Suggested checks:

- Start with one environment and a slow hurdle frequency.
- Confirm the selected dynamic actor has a collision shape.
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
- Confirm type-specific state is populated:
  - `current_gap_offset` for `shifting_gap`
  - `current_step_height` for `changing_step_height`
  - `current_ramp_angle` for `time_varying_ramp`

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

## 5. Static Design Check

Goal: verify the scaffold remains statically consistent without running simulation.

```bash
python tools/check_terrain_design.py
```

Expected result:

- All four obstacle type names are present in code, docs, and the viewer script.
- `DYNAMIC_TERRAIN_SUITES` includes at least four layouts each for `pure_hurdle`, `pure_step`, `pure_gap`, and `pure_ramp`, and at least three layouts for `mixed`.
- The viewer imports Isaac Gym before torch.
- The viewer does not create a PPO runner or wandb run.
- Dynamic obstacles remain disabled by default.

## 6. Task Profile Check

Goal: confirm task-level names exist without changing original `a1` or `go1`.

Expected registry entries:

- `a1_dynamic_hurdle` -> `pure_hurdle`
- `a1_dynamic_step` -> `pure_step`
- `a1_dynamic_gap` -> `pure_gap`
- `a1_dynamic_ramp` -> `pure_ramp`
- `a1_dynamic_mixed` -> `mixed`

## 7. Future Training Check

Training is not part of this task.

Only after viewer, collision, reset, suite-layout, and static-baseline checks pass should future work consider:

- exposing dynamic obstacle state to privileged observations,
- training separate Phase 1 base policies on the pure suites,
- distilling or combining with mixed layouts in Phase 2,
- running small-scale smoke training,
- then running full training comparisons.
