# Environment Setup

This stage does not run training, evaluation, or experiments. It only covers environment setup notes, lightweight import checks, static code checks, and the terrain-generation implementation scaffold.

## Recommended Conda Environment

```bash
conda create -n parkour python=3.8 -y
conda activate parkour
```

## PyTorch

The project README recommends CUDA 11.3 PyTorch:

```bash
pip3 install torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio==0.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
```

Make sure this CUDA build matches the local NVIDIA driver and CUDA runtime.

## Isaac Gym

Isaac Gym must be downloaded manually from NVIDIA. It is not installed from PyPI in the normal way.

Possible install locations:

- `~/isaacgym`
- `<repo>/isaacgym`
- any local directory where the downloaded Isaac Gym package is unpacked

Install the Python package from the Isaac Gym `python` directory:

```bash
cd /path/to/isaacgym/python
pip install -e .
```

The original README says the project was trained with Isaac Gym Preview 3, with Preview 4 also appearing usable. If simulation errors appear, record the exact Isaac Gym Preview version.

## Editable Installs

From the repository root:

```bash
cd rsl_rl && pip install -e .
cd ../legged_gym && pip install -e .
```

## Other Dependencies

```bash
pip install "numpy<1.24" pydelatin wandb tqdm opencv-python ipdb pyfqmr flask
```

## Lightweight Checks

Allowed checks for this stage:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
python -c "import numpy; print(numpy.__version__)"
```

Local check result on this machine after the second setup pass:

- `conda` and `mamba` are not available on PATH, so the requested Python 3.8 conda env could not be created here.
- A project-local fallback venv was created at `.venv-parkour` with Python 3.10.20.
- Python path: `/home/shiyixiao/RobotProject/extreme-parkour/.venv-parkour/bin/python`.
- The exact README PyTorch pin `torch==1.10.0+cu113` is not available for Python 3.10, so the closest CUDA 11.3-compatible install was used:
  - `torch==1.11.0+cu113`
  - `torchvision==0.12.0+cu113`
  - `torchaudio==0.11.0+cu113`
- `torch.cuda.is_available()` reports `False`.
- `torch.version.cuda` reports `11.3`.
- `nvidia-smi` is present but GPU/NVML access is blocked by the operating system in this session.
- `numpy==1.23.5` is installed.
- `rsl_rl` editable install completed.
- `legged_gym` editable install completed with `--no-deps` because `isaacgym` is not available on PyPI and must be installed manually from NVIDIA's package.
- `legged_gym` and `rsl_rl` import successfully.
- `isaacgym` is not installed, so imports that traverse `legged_gym.utils.helpers` or instantiate Isaac Gym environments are still blocked.

Current Isaac Gym-focused check:

- Branch: `feature/dynamic-terrain-generation`.
- Working tree was clean before this documentation update.
- Active env remains `.venv-parkour`.
- Python path remains `/home/shiyixiao/RobotProject/extreme-parkour/.venv-parkour/bin/python`.
- Python version remains `3.10.20`.
- Torch remains `1.11.0+cu113`.
- `torch.version.cuda` remains `11.3`.
- In this Codex shell, `torch.cuda.is_available()` reports `False`.
- In this Codex shell, `nvidia-smi` fails with GPU/NVML access blocked by the operating system.
- No Isaac Gym directory, `isaacgym/python` directory, or Isaac Gym archive was found under `/home/shiyixiao` with the requested searches.

Use the fallback venv with:

```bash
source .venv-parkour/bin/activate
```

or call Python directly:

```bash
.venv-parkour/bin/python -c "import torch; print(torch.__version__)"
```

## Isaac Gym Blocker On This Machine

No local Isaac Gym directory was found under `/home/shiyixiao` with:

```bash
find /home/shiyixiao -maxdepth 3 -type d -name isaacgym
find /home/shiyixiao -maxdepth 5 -type d -path "*/isaacgym/python"
find /home/shiyixiao -maxdepth 5 \( -name "*IsaacGym*.tar.gz" -o -name "*isaacgym*.tar.gz" -o -name "*IsaacGym*.zip" -o -name "*isaacgym*.zip" \)
```

To finish the simulation environment:

1. Download Isaac Gym Preview 4 manually from NVIDIA Developer: https://developer.nvidia.com/isaac-gym
2. Extract it to one of:
   - `/home/shiyixiao/isaacgym`
   - `/home/shiyixiao/RobotProject/extreme-parkour/isaacgym`
3. Confirm one of these files exists:
   - `/home/shiyixiao/isaacgym/python/setup.py`
   - `/home/shiyixiao/RobotProject/extreme-parkour/isaacgym/python/setup.py`
4. Install it inside the active env:

```bash
source /home/shiyixiao/RobotProject/extreme-parkour/.venv-parkour/bin/activate
cd /home/shiyixiao/isaacgym/python
pip install -e .
```

or, if extracted inside the repo:

```bash
source /home/shiyixiao/RobotProject/extreme-parkour/.venv-parkour/bin/activate
cd /home/shiyixiao/RobotProject/extreme-parkour/isaacgym/python
pip install -e .
```

Then run:

```bash
python -c "import isaacgym; print('isaacgym ok')"
python -c "from isaacgym import gymapi, gymtorch; print('gymapi/gymtorch ok')"
python -c "from legged_gym.utils.dynamic_obstacles import DynamicObstacleManager; print('DynamicObstacleManager ok')"
```

## Common Troubleshooting

- `ModuleNotFoundError: isaacgym`: download Isaac Gym manually, then run `pip install -e .` from `/path/to/isaacgym/python`.
- CUDA / PyTorch mismatch: install the PyTorch wheel matching the local CUDA/driver combination. The README command targets CUDA 11.3.
- `numpy` too new: use `numpy<1.24`, because older Isaac Gym / terrain utilities may break with newer NumPy APIs.
- WandB login prompts: training supports `--no_wandb`; use it when logging is not needed.
- Headless machine with no viewer: do not force graphical runs. Later viewer checks can use the project `--web` option or a machine with display support.
- GPU memory issues: reduce `--num_envs`, `--rows`, and `--cols` for small visual checks. Do not start full training in this stage.
- Isaac Gym Preview issues: note whether Preview 3 or Preview 4 is installed and keep the error logs.

## Not In Scope

Do not run:

```bash
python train.py ...
python play.py ...
python eval.py ...
```

Training, formal evaluation, and experiments are intentionally deferred.
