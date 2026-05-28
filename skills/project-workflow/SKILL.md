---
name: project-workflow
description: Apply the extreme-parkour repository's local development workflow. Use when Codex is running commands, editing code, creating branches, preparing commits, giving runnable commands in chat, debugging Isaac Gym/Python environment issues, or reasoning about repository layout in `/home/zhijie/extreme-parkour`.
---

# Project Workflow

## Overview

Use this skill to work inside the `extreme-parkour` repository without losing project-specific operating context. Follow these constraints before running commands, editing files, or giving command snippets to the user.

## Repository Layout

- Treat `plots/` as the home for plotting scripts and generated plots.
- Treat `scripts/` as the record of commands or scripts used to run experiments; some files are notes or reminders.
- Treat `skills/` as the project-local knowledge base. Keep durable workflows, architecture notes, debugging notes, and project decisions there.

## Runtime Environment

- Assume the remote machine is Linux with GUI access, one RTX 3090 GPU, and no `sudo` privilege.
- Run Python scripts through the `parkour` conda environment:

```bash
conda run -n parkour python path/to/script.py
```

- If Isaac Gym fails because `libpython3.8.so.1.0` cannot load, retry with this environment variable:

```bash
export LD_LIBRARY_PATH=/home/zhijie/apps/miniconda3/envs/parkour/lib
```

## Git Workflow

- Use Git for version control awareness.
- Make commits only when the user explicitly asks.
- When asked to commit multiple unrelated changes, split commits by purpose.
- Use Conventional Commits format for all commit messages.
- Do not create or work on a `codex/`-prefixed branch in this repository.
- Respect unrelated worktree changes as user-owned unless the user explicitly asks to revert them.

## Commands In Chat

When the user asks for a command:

- Replace placeholders with the user's actual argument values whenever possible.
- Omit arguments whose values are just defaults.
- Do not include `conda run -n parkour` in the displayed command, even though executed Python commands should use the env.
- Do not include `--device` flags in the displayed command.

## Collaboration Style

- Be brief unless the user asks for detail.
- Prefer updating project-local skills over creating standalone docs when work produces durable project knowledge.
