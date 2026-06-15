---
name: ai-image-workflow
description: Use when planning AI-generated bitmap images for extreme-parkour slides or reports, including when to use placeholders, how to avoid text-heavy generated images, and how to constrain robot parkour scenes by obstacle family before using the imagegen skill.
---

# AI Image Workflow

## Overview

Use this skill when a slide or report would benefit from an AI-generated illustration, especially for training pipelines, conceptual comparisons, or robot parkour scenes.

## Workflow

1. For oral slides, do not generate images immediately unless the user explicitly approves the concept.
2. Add a `% TODO(image-gen): ...` comment at the intended TeX location.
3. In the comment, describe the image purpose, composition, obstacle family, and any labels that should be added later outside the generated image.
4. Keep generated images mostly free of embedded text. Add text manually in LaTeX or post-processing with a sans-serif font, preferably Computer Modern Sans Serif.
5. If a generated frame shows robot parkour, include only one obstacle type per frame. Do not mix hurdles, gaps, steps, and tilted pads in the same generated scene unless the user explicitly asks for a mixed-demo illustration.
6. Use generated bitmap images for visual scenes or conceptual backgrounds; use LaTeX/TikZ or normal plotting for precise diagrams, equations, and labels.
7. For curriculum illustrations, the user may prefer a flat panel grid of simulator-style screenshots rather than a single perspective view of multiple tiles. If some panels are accepted and others need revision, preserve the accepted panels with local image compositing instead of regenerating the whole image.

## Suitable Concepts

- Static-to-dynamic task transition: one A1 robot approaching a single moving hurdle.
- Terrain curriculum: a 2-by-3 contact-sheet grid where columns are terrain families and rows are difficulty levels; each panel should resemble an Isaac Gym screenshot and include the robot for scale. Keep user-approved versions with a suffix before iterating, and prefer local compositing or rollback when a generated revision improves one detail but weakens the overall figure. Add row/column labels outside the generated image in LaTeX.
- Dynamic latent recovery: a clean conceptual image with a robot, depth camera cone, and one visible moving gap, with labels added outside the image.
- Training pipeline: generate background panels or icon-like scenes, then overlay arrows and text manually.

## Avoid

- Text-heavy generated diagrams.
- Ambiguous mixed-obstacle scenes when the slide is about one family.
- Dark, blurry, or decorative images that hide the actual robot or obstacle state.
