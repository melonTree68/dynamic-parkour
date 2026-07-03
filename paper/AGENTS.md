# Paper Writing Guidelines

## Basic information

- 作者是 Zhijie Chen 和 Shiyi Xiao。不要标 equal contribution，Zhijie Chen 位于第一位，Shiyi Xiao 位于第二位。
- 附录和 references 都不算进 8 页篇幅限制里。不要太在意 8 页篇幅限制，多写一些，宁愿多不愿少，力求内容充实，篇幅超了的话再删。尽量让篇幅长一些。
- 项目代码作为一个 Git repo 体现，URL 是 `https://github.com/melonTree68/extreme-parkour`，体现在 abstract 里。
- 在附录里加一个 author contributions section，大致内容见下方 author contributions 节。

## Author contributions

### Zhijie Chen's contribution：

- System design
  - designed the dynamic-obstacle infrastructure solution
  - designed the DAgger-style imitation pretraining stage
  - designed the hybrid-recovery-mode (ROA and teacher-student) environment latent augmentation
  - designed the depth encoder loss integration during camera distillation
- Algorithm implementation
  - implemented and tuned the dynamic-obstacle parkour tasks
  - implemented DAgger-style imitation pretraining
  - implemented environment latent augmentation via dynamic obstacle states
  - implemented hybrid recovery modes (ROA and teacher-student)
  - integrated depth encoder loss during camera distillation
- Experiment design and execution
  - designed and conducted ablation experiments (see the table below for comparison targets)
- Data collection and analysis
  - analyzed experiment results to guide subsequent experimental design
- Report writing and editing
  - wrote the project proposal
  - wrote the midterm report
  - made the oral presentation slides
  - wrote the final paper

Comparison targets for ablation experiments:

| imitation pretrain? | env latent aug? | recovery mode | terrain | `proj_name` |
| :---: | :---: | :---: | :---: | --- |
| no | no | N/A | static | `original-pipeline-static-terrain` |
| no | no | N/A | dynamic | `original-pipeline-dynamic-terrain` |
| yes | no | N/A | dynamic | `imitation-pretrain-dynamic-terrain` |
| yes | yes | ROA | dynamic | `augment-latent-roa-dynamic-terrain` |
| yes | yes | teacher-student | dynamic | `augment-latent-ts-dynamic-terrain` |
| yes | yes | hybrid | mixed | `augment-latent-hybrid-mixed-terrain` |

### Shiyi Xiao's contribution：

- 探索了 dynamic-obstacle parkour task 解决方案（用词保守一些，只是探索，没有任何有用产出）

## Available resources

- project-local skills
- `paper/reference` 里有：
  - 原论文 TeX source：可直接把图拿来用
  - project proposal：有部分内容过时，注意区分；因为 final paper 结构上需要更完整，所以有些需要写进去的内容 midterm report 和 oral slides 里没有，可以从 proposal 中借鉴。
  - midterm report：有少量措辞不是我想要的样子，如果和其他地方的 narrative 或措辞冲突，不要以 midterm report 为准。
  - oral slides：这里面的 narrative、story、内容措辞都完全是我想要的样子，以它为准，以它为主线。因为是 oral presentation slides，所以内容比较简略，且不满足 final paper 要求的结构完整性，需要做不小的扩写。可以复用其中的文字、图表等任何内容。因为当时项目未完全完成，slides 里没有 depth encoder loss 的内容，final paper 里需要有。
- 暂时忽略 `paper/demo` 下的内容，不要在论文中提及它。我后续会整理成合适的 demo video。
- `paper/figures` 下是 oral slides 用的所有图。final paper 的图与其统一颜色等规范；可以直接或部分复用里面的 plotting scripts。depth enc loss 实验的制图在其中是没有的，因为当时还没做这个实验。
- final paper LaTeX template 已经放好了，直接编辑它即可。

## Miscellaneous instructions

- 注意使用 `ai-diagram-gen` 和 `latex-workflow` skill。画图也要遵守 `oral-plotting` skill 的规定。
- 要求 final paper 至少包含两张 AI-generated diagrams，一张 demonstrate training pipeline，一张 illustrate curriculum learning。后者 `paper/figures/curriculum_tiles_labeled.png` 就已经是一份了，当时用于 oral slides，如有不妥之处就重新生成。
- You can and should ask as many questions as needed in plan mode to clarify all requirements.
- It turns out that integrating depth encoder loss during camera distillation did not bring substantial benefit. Report it honestly and analyze possible reasons.
- bibliography 用 natbib。

## Oral slides materials

以下是当时做 oral slides 时的一些材料。其中的 narrative、story、内容措辞等都完全是我想要的样子。就在满足结构要求的基础上，大致按照它和 `paper/reference/oral_slides` 的内容来写 paper 的核心部分。当然，这是大纲，需要大幅扩写。

### What this project has achieved

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

### Slides structure

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
- Conclusions and future directions
