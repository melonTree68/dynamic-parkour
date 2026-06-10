# Proposal And Midterm Notes

## Project Direction

The project extends `Extreme Parkour with Legged Robots` from static obstacle tracks to dynamic-obstacle parkour. The baseline trains a privileged simulation policy and distills it to a deployable depth-based policy. The extension asks whether that staged framework can handle time-varying geometry and support surfaces.

The main dynamic obstacle families are:

- Moving hurdles.
- Shifting gaps or moving takeoff/landing supports.
- Time-varying ramps or tilted pads.
- Steps with changing height.
- Mixed dynamic-demo tracks.

## Environment Latent Augmentation Proposal

The proposed next-stage feature augments latent environment information with dynamic obstacle state. Candidate state includes current hurdle position, gap configuration, step height, and ramp or tilted-pad angle. There is no separate planned augmentation beyond dynamic obstacle state; the broader phrasing is the project narrative.

The deployable depth/camera policy should be trained to recover these quantities explicitly or implicitly from observations. Candidate approaches:

- ROA-style latent estimation for dynamic environment state.
- Teacher-student distillation from a privileged dynamic-state teacher to a deployable student.
- Hybrid latent estimation plus distillation.

The choice should be empirical, based on performance and training stability.

## Midterm Scope Update

The robust-depth-perception branch from the original proposal was dropped for the midterm because current experiments are simulator-only and time is limited. The project focus is now dynamic-obstacle infrastructure and training stability.

Implemented midterm infrastructure:

- `a1_dynamic` task with scripted obstacle actors.
- Unified terrain-parameter interface for obstacle counts, dimensions, amplitudes, periods, spacing, and difficulty-interpolated ranges.
- Dynamic terrain metadata for obstacle pose specs, motion groups, goal groups, and terrain difficulty.
- Runtime scripted obstacle updates through Isaac Gym actor root states.
- Dynamic height-scan overlay for privileged terrain observations.
- Dynamic waypoint updates for goals tied to moving support surfaces.
- Rollout video recording in `play.py`.
- DAgger-style imitation pretraining before RL fine-tuning.

## Preliminary Baselines

Available midterm numbers used mean waypoints reached during evaluation:

| Run | Checkpoint | Waypoints | Reward |
| --- | ---: | ---: | ---: |
| Static base | 9500 | 0.996 | 18.73 |
| Static distill | 10000 | 0.936 | 18.26 |
| Dynamic base | 38500 | 0.399 | 9.33 |
| Dynamic distill | 7000 | 0.192 | 8.51 |
| DAgger + dynamic base | 17500 | 0.704 | 19.35 |

Interpretation:

- The static-terrain pipeline reproduces expected behavior in available logs.
- Directly applying the original base pipeline to dynamic terrain transfers poorly.
- Static-expert DAgger pretraining gives a better starting point for dynamic RL fine-tuning.
- Dynamic distillation is not yet a fair final comparison because that run was incomplete at midterm.

## Evaluation Priorities

Future runs should report results by dynamic obstacle family rather than only aggregate waypoint count. Useful failure categories are mistimed takeoff, obstacle collision, unstable landing, and poor timing around moving support surfaces.
