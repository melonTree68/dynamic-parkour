# Project Development Guidelines

## Project Structure

- `plots/`: stores plotting scripts and generated plots.
- `scripts/`: records commands or scripts used to run experiments; some are notes/reminders.
- `skills/`: project-specific skills directory; project knowledge and workflows should be maintained here, not in Codex's global skills directory.

## Basic Information

- This remote machine is a Linux machine with 1x RTX 3090 GPU. The machine has GUI. I have no `sudo` privilege on it.
- This project uses conda env `parkour`. Use `conda run -n parkour` to run any Python scripts.
- If Isaac Gym loading fails on `libpython3.8.so.1.0`, use `export LD_LIBRARY_PATH=/home/zhijie/apps/miniconda3/envs/parkour/lib`.

## Version Control

- Use Git for version control.
- Make commits only when I ask explicitly.
- When making commits, do not put all changes into one commit; instead, you should make one commit for one purpose.
- All future commit messages must use the Conventional Commits format.
- Do not create and work on a `codex/`-prefixed branch.

## Chat Instructions

- When I ask you to provide a command, if possible:
  - Replace placeholders (e.g., xxx-xx) with my actual argument values.
  - If the value of an arg is just the default, omit it in the output command.
- Be brief unless otherwise specified.
- When outputing commands **in chat**, do not output `conda run -n parkour` and `--device` flags.

## Documentation Management Principles

**Core principle**: Skills are the core documentation repository of this project, responsible for knowledge management and continuity.

### Skill Documentation Management

1. **Archive knowledge in Skills**

   * Any valuable information, including workflows, solutions, architecture design, and debugging experience, should be appended to the most relevant project-local skill under `skills/`.
   * If no suitable skill exists, use `skill-creator` to create a new skill under `skills/`.
   * Skill documents should be continuously updated to reflect the latest project state.

2. **Update Skills after task completion**

   * Feature development: update the relevant skill's workflow and usage instructions.
   * Bug fixes: record the issue and solution in the skill's "Common Issues" or "Known Issues" section.
   * Performance optimization: update best practices and configuration parameters in the skill.
   * Architecture changes: update architecture diagrams and core concept descriptions in the skill.

3. **Skills as the basis for collaboration**

   * Other developers can quickly understand subsystems by reading skills.
   * Skills provide enough context for modifying related code.
   * Skills **record design decisions and historical evolution**.

4. **Minimize other documentation**

   * Do not create unless necessary:

     * Standalone documents under `docs/`
     * `README.md` files in subdirectories
     * Task completion reports or temporary documents

   * Reason: scattered documentation is hard to maintain and easily becomes outdated; centralized skill management is more efficient.
