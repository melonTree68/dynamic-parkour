---
name: project-story
description: Use when explaining, framing, or updating the extreme-parkour project narrative for reports, oral presentations, introductions, conclusions, or contribution summaries, especially the story from static A1 parkour to dynamic obstacles, imitation pretraining, dynamic environment latent augmentation, mixed terrain, and depth distillation.
---

# Project Story

## Overview

Use this skill to present the project as a coherent research story rather than a list of code changes. Verify details against source code and current logs before using numbers.

## Narrative

The project extends `Extreme Parkour with Legged Robots` from static obstacle tracks to dynamic-obstacle parkour. The baseline trains a privileged simulation policy, then distills it to a deployable depth-based policy. This project asks whether that staged framework can handle time-varying obstacle geometry and support surfaces.

The work has evolved through these stages:

1. Reproduce and use the original static A1 parkour pipeline as the baseline.
2. Build `a1_dynamic`, a dynamic-obstacle task that preserves the A1 parkour interface while replacing static obstacle families with scripted moving actors.
3. Show that the original pipeline degrades on dynamic terrain.
4. Add static-expert DAgger-style imitation pretraining to provide a better starting point for dynamic base RL fine-tuning.
5. Add dynamic environment latent augmentation so policies can condition on, recover, or deliberately suppress dynamic obstacle state.
6. Introduce `a1_mixed` to keep useful dynamic families while suppressing latent state for hurdle and tilted-pad families where augmentation was not beneficial.
7. Add optional depth encoder scan-latent loss during camera distillation to stabilize depth latent recovery.

## Emphasis

- Treat dynamic obstacle infrastructure as important but not the core contribution.
- Treat environment latent augmentation and recovery as the core technical contribution.
- Mention imitation pretraining as a practical training-stability bridge from static to dynamic parkour.
- Do not mention the video recorder in oral presentation slides unless the user explicitly asks.

## Results Boundaries

Use available log data when present. If a core experiment directory is empty or lacks `metrics.csv` or `metrics_all.csv`, mark slide/report locations with `% TODO(missing-data): ...` and ask the user for the intended analysis instead of inventing results.
