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

Use compact labels tied to the next relevant obstacle or current goal support:

- Hurdles: relative x position, velocity or phase, height, and crossing index.
- Gaps: relative takeoff/landing support positions, effective gap size, motion phase, and linked moving-goal offset.
- Steps: current top height, vertical velocity or phase, and nominal sampled height.
- Tilted pads: current roll angle, roll velocity or phase, roll sign, and support dimensions.

Prefer robot-relative or goal-relative labels over absolute world coordinates for deployable recovery. Keep full-course state as an ablation, not the default interface, unless experiments show far-future obstacle state improves stability.

## Extension Paths

- Extend privileged latent: append compact dynamic state to the current `n_priv_latent` path so the privileged teacher can use it during base RL.
- Extend explicit privileged estimator: add dynamic state to a supervised estimator target if it should be recovered from proprioception/history or other non-visual observations.
- Extend history latent alignment: make the history encoder match a privileged latent that includes dynamic state, then check whether proprioceptive history alone can infer the dynamic state well enough.
- Extend depth distillation: make the depth encoder recover scan/dynamic latent from depth and train the depth actor against teacher actions and yaw, optionally with explicit dynamic-state prediction loss.
- Hybrid: combine explicit dynamic-state prediction with action/yaw distillation and compare stability against implicit-only distillation.

## Open Decisions

- Whether dynamic state belongs in `n_priv`, `n_priv_latent`, a separate auxiliary head, or a dedicated dynamic latent subvector.
- Whether estimator supervision should use MSE on raw physical quantities, normalized quantities, phase embeddings, or sin/cos phase encoding.
- Whether camera/depth can observe each dynamic family well enough to recover current state without privileged phase information.
- Whether train-time labels should describe all six obstacles or only the current/next obstacle selected by goal index and robot position.

## Related Skills

- `skills/a1-dynamic-task-design/SKILL.md`: dynamic task metadata, actor runtime, height scans, moving goals, and tuning map.
- `skills/imitation-pretraining/SKILL.md`: static-expert DAgger pretraining before dynamic base RL fine-tuning.
