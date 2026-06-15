# Oral Presentation Slides Preparation Guidelines

## How to build the slides

- Use `pdflatex` with flags `-synctex=1`, `-interaction=nonstopmode`, `-file-line-error`. Do not add other flags.
- Use GNU Make (command `gmake`) to build the slides. The makefile should be minimal. Use one target for one plotting script to avoid unnecessary replotting.

## LaTeX guidelines

- Place figure captions below the figure and table captions above the table.
- Use ``...'' for quotation marks.
- Prefer horizontally arranged columns over vertically stacked content, unless there is a clear layout-related reason.
- Use package `algorithm` and `algpseudocode[noend]` for pseudocode.

## Plotting guidelines

### General guidelines

- Output PDF plots.
- Do not use a single script to generate all plots, to avoid unnecessary replotting.
- Put plotting scripts and generated plots under `oral/figures`.
- CSV eval data are under `legged_gym/logs/proj_name/exptid`. Some evals were run on all terrain families, some separately on each terrain family. Some experiments are not yet finished; the corresponding CSV files will be provided in the future. An empty `legged_gym/logs/proj_name/exptid` folder indicates a started but unfinished experiment. In the slides, you may use these not-yet-available data to make tables or plots. In practice, you must use them, since some core experiments are not finished yet. Mark the corresponding locations in the `.tex` file with `% TODO(missing-data)`, and either comment them out or replace them with placeholders. For these tables or plots, ask me what the corresponding analysis should be; I will tell you, since I know the expected results. Then write the analysis and related content according to what I say.
- You might reuse plotting scripts under `plots`; do not touch them.
- Use the same color for the same training pipeline (imitation learning, ROA, teacher-student, hybrid, and hybrid with depth encoder loss) throughout the slides (and future project report).

### Guidelines for AI-generated images

In many situations, especially when illustrating training pipelines, AI-generated diagrams work better than plain text. When this is the case, use the `image-gen` skill to generate a suitable image.

- Do not include large amounts of text directly in generated images. Generate the image first, then add text manually in post-processing. Use a sans-serif font for the text, preferably Computer Modern Sans Serif.
- For each frame in a generated image, if the frame shows robot parkour, the terrain should contain only one obstacle type rather than a mixture of multiple obstacle types.
- If you think AI-generated images are needed somewhere, do not generate them directly. Instead, place a placeholder at the corresponding location in the `.tex` file and add a comment marked with `% TODO(image-gen)`. In the comment, describe the image you intend to generate so that I can review it before actual generation.

### Guidelines for specific plots

- For camera-distillation training curves, include a horizontal dashed line in the same color for each pipeline to indicate the base RL policy performance. Do not include this line in the legend; describe it in the caption.
- For single-pipeline plots, show error bars and smoothed curves. For multi-pipeline plots, show only smoothed curves; do not show raw curves, as they reduce readability.

## What this project has achieved

See project-local skills for details. Each item has a directly corresponding skill.

- Infrastructure
  - Video recorder: Do not mention it in slides.
  - Dynamic-obstacle task design: Give it moderate emphasis. It took us much effort, but it is not the core contribution of the project. Key features include a unified dynamic-obstacle param-tuning interface and an implementation of dynamic obstacles as Isaac Gym box actors. See Midterm Report, III. Technical Approach, A. Dynamic Parkour Infrastructure for more details.
- Task design
  - `a1_dynamic`
  - `a1_mixed`: Derived from `a1_dynamic`, with env-latent suppression; motivation is documented in detail in skill `a1-mixed-terrain`.
- Training pipeline improvement
  - DAgger-style imitation pretraining: Include a pseudocode in the slides to describe this specific version of DAgger.
  - Env latent augmentation and recovery: You need to read multiple skills, including but not limited to `augment-env-latent` and `a1-mixed-terrain`, as well as Midterm Report, III. Technical Approach, second paragraph, to properly understand it. It is de facto the core contribution of this project.
  - Integration of depth encoder loss in camera distillation stage

## Slides structure

curriculum learning

- Intro
  - Problem motivation
  - Related work and background
- Original training pipeline and experimental setup
  - Two-phase student-teacher training
  - Curriculum learning along terrain dimension
  - (Hyper)param values
- Dynamic-obstacle task design
  - Dynamic-obstacle task design and the `a1_dynamic` task
  - Performance degradation of the original pipeline from static to dynamic terrain
    - Metrics
    - Failure-case analysis: leave the itemize blank; I will fill it and play demo videos myself
- Training pipeline improvement
  - DAgger-style imitation pretraining
  - Env latent augmentation and recovery
    - ROA and teacher-student
    - Comparison of no env latent aug, pure ROA, and pure teacher-student, with corresponding analysis
    - Selection of the best hybrid recovery mode based on performance and training stability
    - Mixed terrain (the `a1_mixed` task)
  - Integration of depth encoder loss in camera distillation stage
  - A final comparison among
    - `original-pipeline-static-terrain/distill-from-15k`
    - `original-pipeline-dynamic-terrain/distill-from-15k-v2-16f4736`
    - `augment-latent-hybrid-mixed-terrain/distill-from-resume-from-imitate-base-15k-100-20k-depth-enc-loss`
    - `augment-latent-hybrid-mixed-terrain/distill-from-resume-from-imitate-base-15k-100-20k-depth-enc-loss-static-eval` (to validate that our training-pipeline improvements preserve the original capability on static terrain)
- Conclusions and future directions
