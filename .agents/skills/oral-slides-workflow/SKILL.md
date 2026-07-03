---
name: oral-slides-workflow
description: Use when creating, editing, or validating the oral presentation slides for extreme-parkour under `oral/`, including Beamer structure, slide narrative, TODO handling for missing experiment data, use of `oral/AGENTS.md`, and constraints around preserving existing `oral/main.tex` content.
---

# Oral Slides Workflow

## Overview

Use this skill for the oral presentation deck in `oral/`. Always read `oral/AGENTS.md` before editing slides, then verify content against project-local skills, source code, and available logs.

## Workflow

1. Put substantial slide content wherever the current deck structure expects it. If the deck already keeps slides directly in `main.tex`, continue there; otherwise a separate TeX file such as `oral/slides.tex` is acceptable.
2. Use `pdflatex` with exactly `-synctex=1 -interaction=nonstopmode -file-line-error`.
3. Use GNU Make through `gmake`; keep the Makefile minimal.
4. Keep one Make target per plotting script so unrelated plots do not regenerate.
5. Prefer horizontal Beamer columns over tall stacked lists.
6. Put figure captions below figures and table captions above tables.
7. Use `algorithm` and `algpseudocode` for pseudocode.
8. If the user gives a page-by-page revision list and asks to avoid page-number churn, maintain a checklist such as `oral/todo.md`, complete all source edits first, then compile once at the end.

## Slide Structure

Do not treat this skill as the source of truth for the slide outline. The slide structure must follow the current `oral/AGENTS.md`, especially its `Slides structure` section. If this skill and `oral/AGENTS.md` diverge, `oral/AGENTS.md` wins.

## Missing Data

When a slide needs not-yet-available results, include `% TODO(missing-data): ...` in the TeX source and either comment out the unavailable content or use an obvious placeholder. Ask the user for the expected analysis before writing conclusions about missing data.

For oral slides, avoid visible wording such as "available logs" or "template" in captions and tables. Use polished presentation wording in visible slide text, and keep run-status details in TeX TODO comments.

## Image Placeholders

If an AI-generated image would help, do not generate it immediately. Add `% TODO(image-gen): ...` near the intended slide location with a concise description of the image concept so the user can review it first.
