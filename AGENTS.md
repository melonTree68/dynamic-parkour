## Basic Information

- This remote machine is a Linux machine with 1x RTX 3090 GPU. The machine has GUI. I have no `sudo` privilege on it.
- This project uses conda env `parkour`. Use `conda run -n parkour` to run any Python scripts.
- If Isaac Gym loading fails on `libpython3.8.so.1.0`, use `export LD_LIBRARY_PATH=/home/zhijie/apps/miniconda3/envs/parkour/lib`.

## Version Control

- Use Git for version control.
- Make commits only when I ask explicitly.
- When making commits, do not put all changes into one commit; instead, you should make one commit for one purpose.
- Do not create and work on a `codex/`-prefixed branch.

## Chat Instructions

- When I ask you to provide a command, if possible:
  - Replace placeholders (e.g., xxx-xx) with my actual argument values.
  - If the value of an arg is just the default, omit it in the output command.
- Be brief unless otherwise specified.
- When **outputing commands in chat**, do not output `conda run -n parkour` and `--device` flag.
