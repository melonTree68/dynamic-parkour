# Usage

This repository is an Isaac Gym based quadruped reinforcement learning project. The two main code components are:

- `legged_gym`: environment, task config, training and evaluation scripts
- `rsl_rl`: PPO implementation used by the project

## What This Repo Trains

The default task is `a1`, but in this repository `a1` is registered to the parkour task, not the standard rough-terrain A1 task.

Relevant files:

- [legged_gym/legged_gym/envs/__init__.py](legged_gym/legged_gym/envs/__init__.py)
- [legged_gym/legged_gym/envs/a1/a1_parkour_config.py](legged_gym/legged_gym/envs/a1/a1_parkour_config.py)

So if you run scripts without overriding `--task`, you are training and evaluating the A1 parkour setup.

## Main Scripts

All main entrypoints are under:

```bash
legged_gym/legged_gym/scripts
```

The most important scripts are:

- `train.py`: train a policy
- `play.py`: load a trained policy and run a visual rollout
- `evaluate.py`: batch evaluation with summary metrics
- `save_jit.py`: export deployment-oriented traced models
- `fetch.py`: copy checkpoints from a remote machine using `ssh` and `rsync`

## Common Workflow

### 1. Enter the Script Directory

From the repository root:

```bash
cd legged_gym/legged_gym/scripts
```

### 2. Train a Base Policy

```bash
python train.py --exptid 001-00-base --device cuda:0
```

Notes:

- `train.py` forces `headless=True`, so training does not open the viewer.
- Logs are written under `legged_gym/logs/<proj_name>/<exptid>`.
- The default `proj_name` is `parkour_new`.
- The default task is `a1`.
- By default the script initializes Weights & Biases logging.

If the remote machine does not have W&B configured, use:

```bash
python train.py --exptid 001-00-base --device cuda:0 --no_wandb
```

### 3. Train a Distillation / Vision Policy

This repository supports a second-stage policy using camera/depth inputs. The expected usage is to resume from a previously trained base run.

```bash
python train.py \
  --exptid 002-00-distill \
  --device cuda:0 \
  --resume \
  --resumeid 001-00 \
  --delay \
  --use_camera
```

Meaning of the important flags:

- `--resume`: enable loading from an existing checkpoint
- `--resumeid`: which previous experiment directory to load from
- `--use_camera`: enable the camera/depth branch
- `--delay`: enable action delay

### 4. Play a Trained Policy

Base policy:

```bash
python play.py --exptid 001-00
```

Distillation / vision policy:

```bash
python play.py --exptid 002-00 --delay --use_camera
```

Notes:

- `play.py` loads from `../../logs/<proj_name>/<exptid>`.
- The run name can be abbreviated to the first 6 characters such as `001-00`.
- The loader will try to match that prefix against directories under the log root.
- If `--checkpoint` is not provided, it loads the latest checkpoint.

Examples:

```bash
python play.py --exptid 001-00 --checkpoint 15000
python play.py --exptid 002-00 --delay --use_camera --checkpoint 8000
```

### 5. Evaluate a Trained Policy

```bash
python evaluate.py --exptid 002-00 --delay --use_camera
```

`evaluate.py` runs many environments in parallel and prints summary statistics, including:

- mean reward
- mean episode length
- mean number of waypoints
- mean edge violation

This is the script to use when you want quantitative comparison instead of just visual inspection.

### 6. Export Models for Deployment

```bash
python save_jit.py --exptid 002-00
```

This exports traced artifacts into the run's `traced/` directory. For example:

```bash
legged_gym/logs/parkour_new/002-00-distill/traced/
```

The export script saves:

- a traced actor model
- a vision-weight file for the depth encoder branch

## Log Directory Layout

The default log root is:

```bash
legged_gym/logs/parkour_new/
```

Each experiment gets its own subdirectory:

```bash
legged_gym/logs/parkour_new/<exptid>/
```

Typical contents include:

- `model_*.pt` checkpoints
- config snapshots
- `traced/` exported deployment files

The scripts in this repository assume this layout.

## Important Arguments

These arguments are defined in `legged_gym/legged_gym/utils/helpers.py`.

- `--task`: task name, default is `a1`
- `--device`: simulation/device target, default `cuda:0`
- `--rl_device`: RL device, default `cuda:0`
- `--exptid`: experiment ID / run name
- `--resume`: resume from checkpoint
- `--resumeid`: experiment directory used when resuming
- `--checkpoint`: specific checkpoint number to load, default is latest
- `--proj_name`: log folder name, default `parkour_new`
- `--use_camera`: enable the vision branch
- `--delay`: enable action delay
- `--nodelay`: disable action delay in viewer/eval-time overrides
- `--num_envs`: override environment count
- `--seed`: set random seed
- `--max_iterations`: override PPO iteration count
- `--web`: use the web viewer
- `--no_wandb`: disable Weights & Biases logging

## Viewer Behavior

`play.py` is the main interactive viewer script.

The repository README documents these controls:

- `ALT + Mouse Left + Drag`: move view
- `[` and `]`: switch robot
- `Space`: pause/unpause
- `F`: switch between free camera and following camera

The script also supports a web viewer with:

```bash
python play.py --exptid 001-00 --web
```

This is useful on headless or remote machines.

## Practical Notes

### W&B

`train.py` initializes W&B by default. If the configured machine does not have access to the expected account or project setup, add `--no_wandb`.

### Default Logging vs Config Name

The PPO config still uses `experiment_name = 'rough_a1'`, but this repository's scripts explicitly write runs under `logs/<proj_name>/<exptid>`, and the default `proj_name` is `parkour_new`. In practice, follow the script behavior and look in:

```bash
legged_gym/logs/parkour_new/<exptid>
```

### Prefix-Based Run Matching

The loader supports abbreviated experiment IDs. If you pass `--exptid 001-00`, it will try to match any directory whose first 6 characters are `001-00`.

This is convenient, but it also means you should avoid reusing the same prefix across unrelated runs.

### Action Delay Behavior

The code has special handling for action delay:

- base training from scratch in headless mode can automatically enable delay scheduling
- evaluation and playback let you force delay behavior with `--delay` or suppress view-time delay with `--nodelay`

If you are reproducing paper-style behavior, keep the same delay-related flags between training and playback/evaluation.

## Remote Checkpoint Fetching

There is a helper script:

```bash
python fetch.py --exptid 001-00 --server vision0
```

But this script contains hardcoded remote paths and machine names tied to the original authors' environment. It is not a general-purpose downloader unless you adapt those paths first.

## Minimal Command Cheat Sheet

From repo root:

```bash
cd legged_gym/legged_gym/scripts
```

Train base:

```bash
python train.py --exptid 001-00-base --device cuda:0 --no_wandb
```

Train vision/distillation:

```bash
python train.py --exptid 002-00-distill --device cuda:0 --resume --resumeid 001-00 --delay --use_camera --no_wandb
```

Play base:

```bash
python play.py --exptid 001-00
```

Play vision:

```bash
python play.py --exptid 002-00 --delay --use_camera
```

Evaluate:

```bash
python evaluate.py --exptid 002-00 --delay --use_camera
```

Export:

```bash
python save_jit.py --exptid 002-00
```

## Reference Files

- [README.md](README.md)
- [legged_gym/legged_gym/scripts/train.py](legged_gym/legged_gym/scripts/train.py)
- [legged_gym/legged_gym/scripts/play.py](legged_gym/legged_gym/scripts/play.py)
- [legged_gym/legged_gym/scripts/evaluate.py](legged_gym/legged_gym/scripts/evaluate.py)
- [legged_gym/legged_gym/scripts/save_jit.py](legged_gym/legged_gym/scripts/save_jit.py)
- [legged_gym/legged_gym/utils/helpers.py](legged_gym/legged_gym/utils/helpers.py)
- [legged_gym/legged_gym/envs/__init__.py](legged_gym/legged_gym/envs/__init__.py)
