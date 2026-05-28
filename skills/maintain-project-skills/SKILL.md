---
name: maintain-project-skills
description: Maintain project-local skill documentation for extreme-parkour. Use after feature development, bug fixes, performance optimization, architecture changes, workflow discoveries, debugging discoveries, or any task that produces durable project knowledge that should live under `skills/` instead of scattered docs.
---

# Maintain Project Skills

## Overview

Use this skill to keep project knowledge centralized under `skills/`. Skills are the primary documentation repository for `extreme-parkour`, responsible for knowledge management and continuity.

## Core Rule

Archive valuable project knowledge in the most relevant project-local skill under `skills/`. Valuable knowledge includes workflows, solutions, architecture design, debugging experience, best practices, configuration parameters, and historical design decisions.

## Update Workflow

1. Identify whether the completed task produced durable knowledge.
2. Find the most relevant existing skill under `skills/`.
3. Append or revise that skill with the new knowledge.
4. If no suitable skill exists, use the `skill-creator` workflow to create a new project-local skill under `skills/`.
5. Validate new or substantially changed skills with the skill validator.

## What To Record

- For feature development, update the relevant skill's workflow and usage instructions.
- For bug fixes, record the issue and solution in a `Common Issues` or `Known Issues` section.
- For performance optimization, update best practices and configuration parameters.
- For architecture changes, update architecture diagrams, core concepts, and design decisions.
- For debugging, record symptoms, root cause, and the smallest reliable fix.

## Documentation Boundaries

- Avoid creating standalone documents under `docs/` unless necessary.
- Avoid creating subdirectory `README.md` files unless necessary.
- Avoid creating task completion reports or temporary documents.
- Prefer one clear skill update over scattered documentation that can become stale.

## Skill Quality

- Keep skill content concise and operational.
- Include enough context for another developer or Codex instance to modify the related subsystem.
- Record design decisions and historical evolution when they affect future work.
- Use references inside the skill only when details are too large for `SKILL.md`.
