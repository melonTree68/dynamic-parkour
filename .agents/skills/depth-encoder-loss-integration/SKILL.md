---
name: depth-encoder-loss-integration
description: Use when enabling, disabling, modifying, or debugging the optional scan-latent depth encoder loss in the camera distillation stage of extreme-parkour, including the `--train_depth_encoder_loss` CLI switch and its single-backward integration with depth actor training.
---

# Depth Encoder Loss Integration

## Scope

This skill is specifically about the optional depth encoder scan-latent matching loss during the camera distillation stage. It is not a general camera distillation guide.

## Loss Being Integrated

The optional loss is enabled by `--train_depth_encoder_loss`:

```text
L_scan = mean(|| stopgrad(scan_latent_teacher) - depth_latent_student ||_2)
```

When disabled, `Loss_depth/depth_encoder` should stay `0` and the default distillation behavior is unchanged.

When enabled, `L_scan` is added to the same loss expression as the existing depth actor losses:

```text
L = L_action + L_yaw + w_dynamic * L_dynamic + L_scan
```

## Implementation Map

- `legged_gym/legged_gym/envs/base/legged_robot_config.py`: default `depth_encoder.train_depth_encoder_loss = False`.
- `legged_gym/legged_gym/utils/helpers.py`: defines `--train_depth_encoder_loss` and writes it into `cfg_train.depth_encoder.train_depth_encoder_loss`.
- `rsl_rl/rsl_rl/runners/on_policy_runner.py`: buffers teacher scan latent and student depth latent, then passes them to `PPO.update_depth_actor()` only when the switch is enabled.
- `rsl_rl/rsl_rl/algorithms/ppo.py`: computes `L_scan` inside `update_depth_actor()` so depth actor and depth encoder gradients are updated in one backward pass.

## Cautions

- Do not enable the old standalone `update_depth_encoder()` call in `learn_vision()` as a shortcut. It would create a second backward/optimizer step over tensors that share the depth encoder graph.
- `depth_actor_optimizer` owns both depth actor and depth encoder parameters, so keep the scan-latent matching loss in the same optimizer step unless intentionally redesigning optimizer ownership.
- Gradient clipping should include both `depth_actor` and `depth_encoder` parameters when this integrated loss path is used.
