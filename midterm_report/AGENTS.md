# Midterm Report Guidelines

Unless explicitly told otherwise, also follow the instructions in `AGENTS.md` at the project root. In particular, note the `Documentation Management Principles`. Some information in that `AGENTS.md` is intended for another remote machine, not this one.

## Author Information

There are two authors, both from Shanghai Jiao Tong University. List them in this order. Do **not** label equal contribution.

1. Zhijie Chen, email `zhijie.chen@sjtu.edu.cn`
2. Shiyi Xiao, email `sjtuxsy-finance-pc@sjtu.edu.cn`

## LaTeX Instructions

- LaTeX compilers are installed locally on this machine.
- Use `-synctex=1`, `-interaction=nonstopmode`, and `-file-line-error` during LaTeX compilation.
- Use GNU Make (the command is `gmake`) for compilation, etc.
- Use `natbib` for bibliography.

## About Plotting

- Place plotting scripts and generated plots under `midterm-report/figures/`.
- Output plots in PDF format.
- You can refer to `plots/` for existing scripts and plots (do not edit or move them). They are intended only as references during development and are not necessarily polished.
- Experiment data are under `legged_gym/logs/{proj_name}/{exptid}/metrics.csv`.
- Use conda env `datasci-py313` for running Python plotting scripts.

## Existing Resources

- The proposal of this project is under `midterm_report/references/proposal/`. Be aware that some ideas have changed since the proposal was written.
- As mentioned in the proposal, the project is built on top of an existing paper. The original paper is `midterm_report/references/original_paper.pdf`.

## Writing Guidelines

### General

The story of our progress should primarily revolve around *infrastructure* because

- There is not too much progress on designing improved training pipelines.
- Even for some already proposed training pipelines, much of the training has not yet finished (due to computational resource limits).

Infrastructure includes:

- A dynamic parkour task (`a1_dynamic`) with a unified terrain parameter tuning interface. Dynamic obstacles are implemented as scripted actors in Issac Gym. Some functionalities are implemented in a similar style to the original `a1` task. Some terrain params are randomly sampled from a difficulty-interpolated range.
- A highly customizable video recorder. Mention the two camera modes.
- An imitation pretraining framework using DAgger. Mention how DAgger is implemented here with a pseudocode block.

### Project Title

Change the title to **Dynamic-Obstacle Parkour with Quadruped Robots**, because the robust depth perception part is likely to be dropped. There are several reasons:

- Time limit.
- All experiments are conducted in Issac Gym, a simulator. There is no opportunity to test the performance of the improved training pipeline (e.g., with various kinds of data augmentation, or temporal fusion, as mentioned in the proposal) in real-world settings. This implies that the effect of our improvement is hard to validate.
- Part of the reasons above are already mentioned in the Potential Risks section of the proposal.

### Overview or Abstract

Chosen project type:
> a research project on quadruped parkour that builds on \emph{Extreme Parkour with Legged Robots}~\citep{cheng2023parkour}

### Technical Approach

- The first two paragraphs of the Technical Plan section of the proposal remain valid. The third paragraph is dropped, as I mentioned earlier in `### Project Title`.
- An imitation pretraining stage is added before the base RL training stage. For reasons and details, see `skills/imitation-pretraining`.
- Use `image-gen` skill to create a training pipeline diagram and insert it into the report.
- Include a pseudocode block for **our implementation** of DAgger in imitation pretraining.

### Preliminary Experiments and Results

Valid results (all under `legged_gym/logs`):

- `original-pipeline-static-terrain`: reproduction
  - `base`
  - `distill-from-15k`: distilled from `base/model_15000.pt`
- `original-pipeline-dynamic-terrain`
  - `base-v2-16f4736`: this is just base
  - `distill-from-15k-v2-16f4736`: distilled from `base-v2-16f4736/model_15000.pt`
- `imitation-pretrain-dynamic-terrain`
  - `resume-from-base-15k`: Using `original-pipeline-static-terrain/base/model_15000.pt` as the expert, we first perform imitation pretraining. The resulting policy is then fine-tuned via RL base training. This directory contains the metrics collected during the fine-tuning process.

When necessary, view the plots you generate to analyze the results yourself.

My observations: The original pipeline performs well on static terrain but poorly on dynamic terrain, likely because dynamic parkour is significantly more challenging and difficult to learn via RL from scratch. Adding imitation pretraining substantially improves the performance of base training on dynamic terrain. The distillation training stage has not yet been completed.
