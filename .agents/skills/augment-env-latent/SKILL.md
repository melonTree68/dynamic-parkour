---
name: augment-env-latent
description: Use when designing, implementing, or evaluating augmentation of latent environment information for `a1_dynamic`; in this project the augmentation specifically means adding dynamic obstacle state to privileged latents, history latent recovery, depth/camera teacher-student distillation, explicit vs implicit latent recovery, and per-family evaluation of whether hurdle, gap, step, or tilted-pad state is recoverable from observations.
---

# Augment Environment Latent

## Overview

The project narrative is to augment latent environment information for `a1_dynamic`. The only planned augmentation is dynamic obstacle state: current hurdle position, moving gap support configuration, step height, tilted-pad/ramp angle, motion phase, velocity, and related timing information.

The original pipeline already contains two latent recovery mechanisms:

1. ROA/RMA-style recovery from proprioceptive history to match privileged latent state during base RL.
2. Teacher-student camera/depth distillation that recovers scan-derived latent and teacher behavior from depth observations.

This dynamic-state augmentation should extend these mechanisms instead of treating ROA-style estimation and teacher-student distillation as entirely new concepts.

## Workflow

1. Read [references/original-pipeline-latent-recovery.md](references/original-pipeline-latent-recovery.md) before modifying model architecture, estimator targets, PPO losses, DAgger updates, or depth distillation.
2. Read [references/proposal-midterm-notes.md](references/proposal-midterm-notes.md) for project motivation, midterm scope, and preliminary dynamic baselines.
3. Read `skills/a1-dynamic-task-design/SKILL.md` before changing dynamic obstacle metadata, actor states, moving goals, dynamic height scans, or per-family terrain generation.
4. Read `skills/imitation-pretraining/SKILL.md` before changing static-expert initialization or DAgger imitation pretraining.
5. Define dynamic-obstacle-state labels from the scripted simulator state first, then decide where to inject or predict them.
6. Evaluate variants by dynamic obstacle family and failure mode, not only aggregate reward or waypoint count.

## Dynamic Obstacle State

The implemented `a1_dynamic` interface appends `env.n_dynamic_env_latent = 30` after the original privileged latent slice and before proprioceptive history. Static `a1` keeps `n_dynamic_env_latent = 0`. The code-only switch lives in `A1DynamicParkourCfg.dynamic_env_latent.recovery_modes`, keyed by obstacle family: `hurdle`, `gap`, `step`, and `tilted_pad`. `dynamic_demo` follows each component group's actual motion type.

The default layout is 2 upcoming groups x 15 features per group:

```text
valid, hurdle_bit, gap_bit, step_bit, tilted_pad_bit,
rel_x_slot0, rel_x_slot1, rel_y, primary_value, value_velocity,
value_acceleration, sin_phase, cos_phase, amplitude, omega
```

`primary_value` is family-specific: hurdle top height, gap effective width, step top height, or tilted-pad roll angle. Position-like values are robot-relative and normalized. Velocity, acceleration, phase, amplitude, and angular frequency come from the scripted simulator state after `_apply_dynamic_poses()` has updated obstacle root states and dynamic motion tensors.

The labels are intentionally low-dimensional. This makes them easy to supervise and analyze, but they may be too small or too hand-designed to produce a large performance gain by themselves. Treat weak gains as an expected possibility rather than an implementation failure.

## Implemented Recovery Paths

- Imitation pretraining is now `imitation pretrain + env latent augmentation`: the student learns privileged-action imitation, history-action imitation, the explicit estimator, and masked ROA-style dynamic-state recovery for families configured as `"roa"`.
- Base RL fine-tuning reuses the augmented observation and actor. The original priv/history latent regularization remains unchanged, and a separate masked dynamic-state recovery loss trains the dynamic history encoder for ROA-mode families.
- Camera teacher-student distillation remains the post-pretrain stage. The depth encoder outputs `scan_latent + dynamic_env_latent + yaw`; teacher-student-mode families use the depth-predicted dynamic state, while ROA-mode families continue to use the history dynamic encoder.
- Old static checkpoints can initialize augmented models through compatible partial loading. Matching weights are copied; expanded linear weights copy old columns and zero-initialize the new dynamic-latent columns.

## Open Decisions

- Whether dynamic state belongs in `n_priv`, `n_priv_latent`, a separate auxiliary head, or a dedicated dynamic latent subvector.
- Whether estimator supervision should use MSE on raw physical quantities, normalized quantities, phase embeddings, or sin/cos phase encoding.
- Whether camera/depth can observe each dynamic family well enough to recover current state without privileged phase information.
- Whether train-time labels should describe all six obstacles or only the current/next obstacle selected by goal index and robot position.

## Related Skills

- `skills/a1-dynamic-task-design/SKILL.md`: dynamic task metadata, actor runtime, height scans, moving goals, and tuning map.
- `skills/imitation-pretraining/SKILL.md`: static-expert DAgger pretraining before dynamic base RL fine-tuning.
