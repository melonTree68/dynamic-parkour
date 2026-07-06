# Dynamic-Obstacle Parkour with Quadruped Robots

## Setup

```bash
conda create -n parkour python=3.8
conda activate parkour
pip3 install torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio==0.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
# Download Isaac Gym from https://developer.nvidia.com/isaac-gym
cd /path/to/isaacgym/python && pip install -e .
cd /path/to/this/repo/rsl_rl && pip install -e .
cd /path/to/this/repo/legged_gym && pip install -e .
pip install "numpy<1.24" pydelatin wandb tqdm opencv-python ipdb pyfqmr flask
```

You may need to set the environment variable `LD_LIBRARY_PATH` to `/path/to/parkour/conda/env/lib`.

## Usage

Run the following commands from `legged_gym/legged_gym/scripts`.

### Common arguments

See `legged_gym/legged_gym/utils/helpers.py` for the full list of arguments.

- `--headless`: enable this on headless machines; do not train camera distillation on headless machines
- `--no_wandb`: disable wandb
- `--device`: device, e.g., `cpu`, `cuda:0`
- `--delay`: add delay
- `--use_camera`: use camera depth input; does not support headless machines
- `--task`: parkour task; only support `a1`, `a1_dynamic` (default), and `a1_mixed`
- `--proj_name` and `--exptid`: checkpoints are saved under `legged_gym/logs/<proj_name>/<exptid>`
- `--resume`, `--resumeid`, and `--checkpoint`: resume training from checkpoint `legged_gym/logs/<proj_name>/<resumeid>/<checkpoint>.pt`; use the latest checkpoint if `--checkpoint` is not provided

Set dynamic environment latent recovery mode on line 9-14 of `legged_gym/legged_gym/envs/a1/a1_dynamic_config.py`.

### Imitation pretraining

```bash
python pretrain_imitation.py --task <task> \
  --expert_proj_name <expert-proj-name> \
  --expert_exptid <expert-exptid> \
  --expert_checkpoint <expert-ckpt> \
  --proj_name <proj-name> --exptid <imitation-exptid>
```

Expert policy will be loaded from `legged_gym/logs/<expert-proj-name>/<expert-exptid>/<expert-ckpt>.pt`

### Base RL training

```bash
# Train base RL from scratch
python train.py --task <task> --proj_name <proj-name> --exptid <base-exptid>
# Fine-tune an imitation-pretrained policy
python train.py --task <task> \
  --resume --resumeid <imitation-exptid> --checkpoint <imitation-ckpt> \
  --proj_name <proj-name> --exptid <base-exptid>
```

### Camera distillation

```bash
python train.py --delay --use_camera --task <task> \
  --resume --resumeid <base-exptid> --checkpoint <base-ckpt> \
  --proj_name <proj-name> --exptid <distill-exptid>
```

Add `--train_depth_encoder_loss` to enable depth encoder scan-latent loss.

### Evaluation

```bash
# Evaluate base policy
python evaluate.py --delay --task <task> \
  --proj_name <proj-name> --exptid <base-exptid> --checkpoint <ckpt>
# Evaluate distillation policy
python evaluate.py --delay --use_camera --task <task> \
  --proj_name <proj-name> --exptid <distill-exptid> --checkpoint <ckpt>
```

Use `--eval_terrain` to evaluate the policy only on specific terrains. If not provided, the task's default terrain split is used.

### Play

```bash
# Play base policy
python play.py --delay --record_video --task <task> \
  --proj_name <proj-name> --exptid <base-exptid> --checkpoint <ckpt>
# Play distillation policy
python play.py --delay --use_camera --record_video --task <task> \
  --proj_name <proj-name> --exptid <distill-exptid> --checkpoint <ckpt>
```

Videos are saved under `videos/<proj-name>/<exptid>/<timestamp>`.

Extra video recording arguments:

- `--video_width` and `--video_height`: video resolution
- `--video_fps`: video frames per second
- `--video_episodes`: number of episodes in each video
- `--video_camera_mode`: recorded camera mode; only support `yaw` (roll/pitch fixed, yaw follows the robot) and `attached` (roll/pitch/yaw all follow the robot)
