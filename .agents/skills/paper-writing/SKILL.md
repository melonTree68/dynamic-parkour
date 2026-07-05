---
name: paper-writing
description: Use when creating, editing, validating, or extending the final paper/report for extreme-parkour under `paper/`, including RSS/IEEE LaTeX structure, final-paper narrative, legacy figure handling, regenerated plots, AI diagram policy, page-limit handling, and paper-specific build workflow.
---

# Paper Writing

## Overview

Use this skill for the final paper under `paper/`. Read `paper/AGENTS.md` and `paper/requirements.md` first, then verify technical claims against project-local subsystem skills and available experiment logs.

## Workflow

1. Edit `paper/paper_template.tex` directly unless the user asks to rename the source.
2. Build with `gmake -C paper`; keep `paper/Makefile` minimal and use one target per plotting script or tightly related figure family.
3. Use `pdflatex -synctex=1 -interaction=nonstopmode -file-line-error`, `bibtex`, then repeated `pdflatex`.
4. Use `natbib` with `plainnat`.
5. Ignore overfull and underfull box warnings unless the user asks for layout cleanup. Do not use sloppy layout workarounds.
6. Do not trim unless the main paper exceeds 9 pages excluding references and appendix.

## Figure and Plot Policy

- Treat `paper/figures/legacy` as the archive of oral-slide scripts, plots, and AI-generated curriculum assets.
- If reusing a legacy script or image, copy it into `paper/figures` and modify only the copy.
- Do not directly reuse legacy PDF plots as final paper artifacts; regenerate final plots from CSVs.
- Keep plot colors consistent with oral/report conventions:
  - static original: blue
  - dynamic original: gray
  - imitation-pretrained dynamic: green
  - ROA: orange
  - teacher-student: purple
  - hybrid mixed terrain: red
  - hybrid with depth encoder loss: teal
- For AI-generated diagrams, keep embedded text minimal and explain labels in LaTeX captions or manual post-processing. Leave a nearby `% TODO(image-gen): ...` comment documenting the intended image.
- For the final training-pipeline figure, regenerate `figures/training_pipeline_ai.png` with `figures/build_training_pipeline.py` from verified demo frames under `figures/training_pipeline_frames/`. Keep stage titles outside the three rounded image frames, place arrows and transition labels in the whitespace between frames, and draw semantic pipeline labels deterministically rather than through image generation. The third-frame MLP glyph is cropped from `paper/reference/original_paper/figures/method_compressed.pdf` into `figures/training_pipeline_assets/mlp_icon_original.png`; the depth rollout is an AI-generated depth-modality image matched to the demo-frame viewpoint and stored as `figures/training_pipeline_assets/depth_rollout_ai.png`.
- Before iterating on `figures/training_pipeline_ai.png`, archive the current output under `figures/training_pipeline_versions/training_pipeline_ai_vNN.png`, using the next version suffix. Keep the latest figure at `figures/training_pipeline_ai.png` so LaTeX and Make targets remain stable.
- When modifying the training-pipeline figure, verify dynamic obstacle appearance against `paper/demo` frames and `legged_gym/legged_gym/utils/terrain.py`: hurdles are moving cuboid blocks, gaps are carved pits with two moving platforms, tilted pads are rolling slabs over pits, and dynamic steps are box-height actors. Reject polished CAD-style tracks, rails/posts, wooden boards, and generic obstacle-course imagery.

## Narrative Decisions

- The story follows: original static pipeline, dynamic-obstacle task, original pipeline degradation, DAgger-style imitation pretraining, dynamic environment latent augmentation/recovery, mixed-terrain latent suppression, depth encoder loss, final comparison.
- Dynamic-obstacle infrastructure can be described in detail; it is important even if environment latent augmentation is the core contribution.
- Report depth encoder loss honestly as a strong but non-improving result rather than claiming a substantial benefit.
- Do not mention `paper/demo` material unless the user explicitly asks to integrate demo videos.

## Validation

- Check the final log for undefined citations, undefined references, missing figures, and LaTeX/package errors.
- Check total PDF page count; if total is already below the main-paper threshold, do not trim.
- Visually inspect rendered pages for obvious missing figures, unreadable tables, or severe float placement problems.
