---
name: a1-mixed-terrain
description: Use when modifying, debugging, training, evaluating, or explaining the `a1_mixed` task, the `mixed_demo` terrain family, or the mixed static/dynamic terrain setting in extreme-parkour, including task registration, terrain dispatch, static-step replacement inside dynamic demo courses, play/evaluate defaults, and tests for mixed terrain metadata.
---

# A1 Mixed Terrain

## Overview

Use this skill to work on the `a1_mixed` task and its `mixed_demo` terrain. The task is a configuration-level variant of `a1_dynamic`: it keeps dynamic obstacle actors through `DynamicLeggedRobot`, but trains on a five-way mix that includes both dynamic actor terrains and static parkour steps.

## Workflow

1. Read `.agents/skills/a1-dynamic-task-design/SKILL.md` before changing dynamic terrain metadata, actor runtime behavior, moving goals, dynamic height scans, or dynamic latent observations.
2. Inspect these files before editing mixed terrain behavior:
   - `legged_gym/legged_gym/utils/terrain.py`
   - `legged_gym/legged_gym/envs/a1/a1_dynamic_config.py`
   - `legged_gym/legged_gym/envs/__init__.py`
   - `legged_gym/legged_gym/scripts/play.py`
   - `legged_gym/legged_gym/scripts/evaluate.py`
   - `legged_gym/legged_gym/tests/test_dynamic_terrain.py`
3. Preserve `a1`, `a1_dynamic`, and `a1_mixed` as switchable CLI tasks. Users should only need to change `--task a1`, `--task a1_dynamic`, or `--task a1_mixed`.
4. After changing mixed terrain behavior, update this skill with durable implementation decisions or deviations.

## Key Facts

- `a1_mixed` registers with `DynamicLeggedRobot`, not a new environment class.
- `A1MixedParkourCfg` inherits from `A1DynamicParkourCfg` so actor slots, dynamic obstacle config, rewards, observations, and dynamic latent dimensions stay compatible with `a1_dynamic`.
- The default `a1_mixed` terrain split is:

```python
"dynamic_hurdle": 0.2
"dynamic_gap": 0.2
"dynamic_tilted_pads": 0.2
"parkour_step": 0.2
"mixed_demo": 0.2
```

- `dynamic_step`, `dynamic_demo`, and unrelated terrain families have zero default weight in `a1_mixed`.
- `mixed_demo` is not a full `parkour_step_terrain` course. It is the `dynamic_demo` sequence with only the single dynamic step obstacle replaced by one static parkour-style heightfield step segment.
- The static step is represented through the terrain heightfield and height scan observations, not through dynamic obstacle actor metadata.

## Terrain Metadata Rules

- Use `DYNAMIC_MIXED_DEMO` so logs and tests distinguish mixed demo tiles from `DYNAMIC_DEMO`.
- Add `mixed_demo` to `terrain_dict` and update `Terrain.make_terrain()` dispatch. The dictionary order and positional `self.proportions[index]` checks must stay aligned.
- Keep the dynamic actor group corresponding to the replaced step inactive with `DYNAMIC_NONE` motion type and parked obstacle specs.
- Keep moving hurdle, gap, and tilted-pad actor metadata consistent with `dynamic_demo`.
- Preserve gap moving-goal mapping with `dynamic_goal_groups`; static step goals should not be mapped to a moving dynamic group.
- Do not change the dynamic latent schema just to represent the static step. The selected latent group for an inactive/static step should produce invalid or zero dynamic features.

## Testing

- Cover task registration for `a1_mixed` and verify it maps to `DynamicLeggedRobot`.
- Verify `a1`, `a1_dynamic`, and `a1_mixed` default terrain distributions remain distinct.
- Test `mixed_demo_terrain()` for eight goals, `DYNAMIC_MIXED_DEMO` family id, inactive step actor group, active hurdle/gap/tilted-pad groups, preserved gap goal mapping, and a nonzero static step in the heightfield.
- Test `Terrain.make_terrain()` dispatch with only `mixed_demo` enabled.
- Update `play.py` and `evaluate.py` smoke checks when their task-specific terrain defaults change.

## Cautions

- Do not modify stale copied files under `legged_gym/legged_gym/scripts/legged_gym/` unless runtime inspection proves they are active.
- Do not create a new environment class for `a1_mixed` unless actor runtime requirements genuinely diverge from `DynamicLeggedRobot`.
- Do not let `play.py` hardcoded overrides collapse `a1_mixed` back to the old `a1_dynamic` terrain set.
