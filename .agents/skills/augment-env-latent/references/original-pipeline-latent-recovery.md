# Original Pipeline Latent Recovery

## Code Map

Core implementation files:

- `legged_gym/legged_gym/envs/base/legged_robot_config.py`: observation dimensions, policy dimensions, PPO algorithm settings, estimator settings, depth encoder settings.
- `legged_gym/legged_gym/envs/base/legged_robot.py`: observation construction and terrain height scan values.
- `rsl_rl/rsl_rl/modules/actor_critic.py`: actor input slicing, scan encoder, privileged latent encoder, history encoder, and inference entry points.
- `rsl_rl/rsl_rl/modules/estimator.py`: explicit privileged-state estimator from proprioception.
- `rsl_rl/rsl_rl/algorithms/ppo.py`: PPO update, privileged/history latent regularization, estimator update, DAgger-style history latent update, and depth distillation losses.
- `rsl_rl/rsl_rl/runners/on_policy_runner.py`: base RL loop and vision/depth distillation loop.
- `rsl_rl/rsl_rl/modules/depth_backbone.py`: depth image encoder and recurrent depth latent/yaw head.

Avoid modifying copied stale files under `legged_gym/legged_gym/scripts/legged_gym/` unless runtime inspection proves they are active.

## Observation Layout

`LeggedRobotCfg.env` defines the actor observation layout:

- `n_proprio = 3 + 2 + 3 + 4 + 36 + 5`.
- `n_scan = 132`.
- `n_priv = 3 + 3 + 3`.
- `n_priv_latent = 4 + 1 + 12 + 12`.
- `history_len = 10`.
- `num_observations = n_proprio + n_scan + history_len * n_proprio + n_priv_latent + n_priv`.

`LeggedRobot.compute_observations()` builds the tensor in this order:

1. `obs_buf`: proprioceptive and command/goal features.
2. `heights`: clipped terrain height samples when `measure_heights` is enabled.
3. `priv_explicit`: base linear velocity and two zeroed 3D placeholders, total `n_priv = 9`.
4. `priv_latent`: domain-randomization latent values: mass parameters, friction, and motor-strength offsets.
5. Flattened proprioceptive history: `history_len * n_proprio`.

The code masks yaw slots `obs_buf[:, 6:8] = 0` before pushing the frame into `obs_history_buf`, so history encoding does not directly receive current yaw information from those slots.

## Actor Latent Structure

`ActorCriticRMA` constructs `Actor` with `num_prop`, `num_scan`, `num_priv_explicit`, `num_priv_latent`, and `num_hist` from env config.

The actor assumes observation order:

```text
prop -> scan -> priv_explicit -> priv_latent -> history
```

Inside `Actor.forward()`:

- Terrain scan values are encoded by `scan_encoder` when `scan_encoder_dims` is not `None`; default dimensions are `[128, 64, 32]`.
- Explicit privileged state is sliced directly from the observation and concatenated into actor input.
- If `hist_encoding=False`, latent comes from `infer_priv_latent(obs)`, which slices `priv_latent` and feeds it through `priv_encoder`; default `priv_encoder_dims` are `[64, 20]`.
- If `hist_encoding=True`, latent comes from `infer_hist_latent(obs)`, which encodes the last `history_len` proprioceptive frames through `StateHistoryEncoder`.
- Actor backbone input is `proprio + scan_latent + priv_explicit + latent`.

This means the original base policy uses privileged latent during ordinary PPO updates, while the history encoder learns to replace that privileged latent for deployment-like inference.

## ROA/RMA-Style History Recovery

There are two related history-latent losses in `PPO`:

1. During `PPO.update()`, the code computes `priv_reg_loss = ||infer_priv_latent(obs) - stopgrad(infer_hist_latent(obs))||_2`. This loss is added to PPO loss with `priv_reg_coef`, scheduled by `priv_reg_coef_schedual`.
2. During `PPO.update_dagger()`, the code freezes privileged latent and trains only `actor.history_encoder` with `hist_latent_loss = ||stopgrad(infer_priv_latent(obs)) - infer_hist_latent(obs)||_2`.

`OnPolicyRunner.learn_RL()` sets `hist_encoding = it % dagger_update_freq == 0` for rollout collection. After PPO update, if `hist_encoding` is true, it calls `self.alg.update_dagger()`. Default `dagger_update_freq = 20`.

Important implication for dynamic-obstacle latent work: if dynamic state is appended to the privileged latent path, the existing history encoder will be asked to infer it from proprioceptive history. That may be useful for motion phase that affects body dynamics, but it may be insufficient for visually observable obstacle state not yet contacted. Test this explicitly rather than assuming it works.

## Explicit Privileged-State Estimator

`Estimator` is a small MLP from proprioception to explicit privileged state:

- Input: `obs[:, :num_prop]`.
- Output: `priv_states_dim = n_priv`.
- Default hidden dims: `[128, 64]`.

`PPO.update()` trains it by MSE against the `priv_explicit` slice:

```text
obs[:, num_prop + num_scan : num_prop + num_scan + priv_states_dim]
```

`PPO.act()` uses `train_with_estimated_states` from config. If true, it clones `obs`, predicts `priv_explicit` from proprioception, writes the prediction back into the explicit privileged slice, then calls the actor. The stored rollout observation still contains the true privileged state, so PPO and estimator losses can use ground truth labels during training.

Important implication: if dynamic obstacle state is put into `n_priv` and `train_with_estimated_states=True`, the estimator will try to recover it from proprioception alone. That is likely inappropriate for future obstacle pose unless the state is indirectly observable through contact/timing. For visually recoverable obstacle state, prefer a depth/camera path or a separate auxiliary head.

## Depth/Camera Teacher-Student Distillation

When `depth.use_camera` is true, `OnPolicyRunner` sets `self.learn = self.learn_vision`.

Runner setup:

- `DepthOnlyFCBackbone58x87` compresses a `58x87` depth image into a vector with the same size as the scan encoder output, currently `32`.
- `RecurrentDepthBackbone` combines depth features with proprioception, runs a GRU with hidden size `512`, and outputs `32 + 2` values through `Tanh`: a depth latent and a yaw correction.
- `depth_actor` is initialized as a deepcopy of `actor_critic.actor`.

Vision loop per step:

1. Teacher scan latent is computed as `actor_critic.actor.infer_scandots_latent(obs)`.
2. The depth encoder receives current depth and proprioception with yaw slots masked, then returns `depth_latent_and_yaw`.
3. `depth_latent = output[:, :-2]` and `yaw = 1.5 * output[:, -2:]`.
4. Teacher action is `actor_critic.act_inference(obs, hist_encoding=True, scandots_latent=None)`.
5. Student observation copies `obs`, replaces yaw slots `6:8` with predicted yaw where `infos["delta_yaw_ok"]` is true, and calls `depth_actor(obs_student, hist_encoding=True, scandots_latent=depth_latent)`.
6. The environment is stepped with student actions after `num_pretrain_iter`; currently `num_pretrain_iter = 0`.

Losses in `PPO`:

- `update_depth_actor()` minimizes action L2 distance between teacher and student plus yaw L2 distance between predicted yaw and observation yaw.
- `update_depth_encoder()` can train depth latent against scan latent, but the runner currently comments this call out.
- `update_depth_both()` can combine scan-latent matching and action imitation, but the runner currently comments this call out too.

Important implication: current active vision training is primarily action/yaw distillation, not explicit depth-latent matching. For dynamic state, add explicit dynamic-state prediction only if it improves stability or interpretability; otherwise an implicit teacher-action loss may already transmit useful timing behavior.

## Dynamic Obstacle State Sources

`DynamicLeggedRobot` already maintains simulator-side tensors that can be converted to privileged dynamic labels:

- `dynamic_family`: current dynamic terrain family per environment.
- `dynamic_difficulty`: curriculum difficulty for the current tile.
- `dynamic_specs`: per-obstacle/slot base specs `[x, y, z, sx, sy, sz, extra]`.
- `dynamic_motion_types`: hurdle, gap, tilted pad, step, or inactive slot IDs.
- `dynamic_motion_groups`: group IDs used to share motion signals across slots.
- `dynamic_goal_groups`: which goals translate with a motion group.
- `dynamic_phase`, `dynamic_amplitude`, `dynamic_period`, `dynamic_time`: sampled motion parameters.
- `dynamic_offset`, `dynamic_velocity`: current scripted state after `_apply_dynamic_poses()`.
- `obstacle_root_states`: current actor root states for all dynamic actors.
- `dynamic_dims`: current actor dimensions.

`_apply_dynamic_poses()` computes sinusoidal offsets and velocities for each obstacle group, maps them to actor slots, writes current root positions/orientations/velocities, and calls `_update_dynamic_goals()`. `_get_heights()` overlays dynamic actor top surfaces onto the terrain height scan.

For a first dynamic latent implementation, derive labels after `_apply_dynamic_poses()` has updated `dynamic_offset`, `dynamic_velocity`, `obstacle_root_states`, and moving goals. Prefer robot-relative features such as next obstacle center minus base position, current support top height minus base height, effective gap endpoints relative to the robot, or current tilted-pad roll.

## Extension Patterns

### Extend Privileged Latent

Use this when the base teacher should condition directly on dynamic state during PPO:

1. Increase `env.n_priv_latent` or split out a new dynamic latent dimension.
2. Append normalized dynamic labels after existing domain-randomization `priv_latent` in `compute_observations()` or a dynamic override.
3. Update policy slicing assumptions and checkpoint compatibility notes.
4. Verify `infer_priv_latent()` and `infer_hist_latent()` still produce equal output dimensions.
5. Evaluate whether `update_dagger()` can train history latent to match the expanded privileged latent.

Risk: history-only recovery may be weak for future obstacle motion. This can make the history encoder chase unobservable labels.

### Extend Explicit Estimator

Use this only for dynamic quantities that should be predicted from proprioception or short history without depth:

1. Increase `env.n_priv` and `estimator.priv_states_dim` consistently.
2. Add labels to the `priv_explicit` slice.
3. Keep `train_with_estimated_states=True` only if replacing true labels with estimator output during action selection is desired.

Risk: the estimator currently sees only `n_proprio`, not the full history or depth image.

### Extend Depth Distillation

Use this for visually recoverable dynamic obstacle state:

1. Decide whether dynamic labels supervise the depth encoder output, an auxiliary head, or the actor input latent.
2. If replacing/augmenting scan latent, ensure `depth_actor(..., scandots_latent=depth_latent)` receives the expected dimension.
3. Consider re-enabling a version of `update_depth_encoder()` or `update_depth_both()` with dynamic-state terms.
4. Keep action/yaw distillation as the behavioral teacher signal unless ablations show explicit labels are enough.

Risk: the current depth encoder output is `32 + 2`; adding dynamic state may require a wider output and matching actor input changes.

## Evaluation Checklist

For every variant, log at least:

- Aggregate reward and mean waypoints.
- Per-family waypoints/success for hurdle, gap, step, tilted pads, and dynamic demo.
- Dynamic-state prediction loss, if explicit labels are trained.
- History latent loss and privileged regularization loss when expanding privileged latent.
- Depth actor/yaw loss and any depth/dynamic latent loss during distillation.
- Failure categories from videos: mistimed takeoff, collision, unstable landing, and moving-support timing errors.
