---
name: a1-mixed-terrain
description: Use when modifying, debugging, training, evaluating, or explaining the `a1_mixed` task, the `mixed_demo`, `mixed_tilted_pads`, or `mixed_hurdle` terrain family, or the mixed static/dynamic terrain setting in extreme-parkour, including task registration, terrain dispatch, static-step replacement inside dynamic demo courses, play/evaluate defaults, and tests for mixed terrain metadata.
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
"mixed_hurdle": 0.2
"dynamic_gap": 0.2
"mixed_tilted_pads": 0.2
"parkour_step": 0.2
"mixed_demo": 0.2
```

- `dynamic_hurdle`, `dynamic_tilted_pads`, `dynamic_step`, `dynamic_demo`, and unrelated terrain families have zero default weight in `a1_mixed`.
- `mixed_demo` is not a full `parkour_step_terrain` course. It is the `dynamic_demo` sequence with only the single dynamic step obstacle replaced by one static parkour-style heightfield step segment. Its hurdle and tilted-pad groups suppress dynamic latent features, while its gap group keeps dynamic latent features.
- The static step is represented through the terrain heightfield and height scan observations, not through dynamic obstacle actor metadata.
- `mixed_tilted_pads` intentionally looks and moves like `dynamic_tilted_pads`, including dynamic tilted-pad actors and height overlays, but its terrain family id suppresses dynamic obstacle state latent features for that terrain in `a1_mixed`.
- `mixed_hurdle` intentionally looks and moves like `dynamic_hurdle`, including normal `DYNAMIC_HURDLE` actor metadata, but suppresses dynamic obstacle state latent features for those hurdle groups in `a1_mixed`.

## Experimental Findings

- Env latent augmentation on `dynamic_tilted_pads` was a negative improvement in both ROA-style recovery and teacher-student depth recovery experiments. Keep this result in mind when reporting per-family augmentation outcomes or deciding future recovery modes.
- In camera distillation experiments on `dynamic_hurdle`, imitation learning performed best among ROA, imitation learning, and teacher-student variants. The working hypothesis is that hurdle motion amplitude and speed are small, and the hard part is learning behavior robust to Isaac Gym collision artifacts rather than recovering precise obstacle state.
- The resulting design choice is to keep `a1_dynamic` unchanged and route only `a1_mixed` through latent-suppressed variants: `mixed_tilted_pads` for tilted pads and `mixed_hurdle` for hurdles. These preserve the same terrain/actor experience while zeroing dynamic state information for those families.

## Terrain Metadata Rules

- Use `DYNAMIC_MIXED_DEMO` so logs and tests distinguish mixed demo tiles from `DYNAMIC_DEMO`.
- Use `DYNAMIC_MIXED_TILTED_PADS` so `a1_mixed` can distinguish latent-suppressed tilted-pad tiles from normal `DYNAMIC_TILTED_PADS` tiles.
- Use `DYNAMIC_MIXED_HURDLE` so `a1_mixed` can distinguish latent-suppressed hurdle tiles from normal `DYNAMIC_HURDLE` tiles.
- Add `mixed_demo`, `mixed_tilted_pads`, and `mixed_hurdle` to `terrain_dict` and update `Terrain.make_terrain()` dispatch. The dictionary order and positional `self.proportions[index]` checks must stay aligned.
- Keep the dynamic actor group corresponding to the replaced step inactive with `DYNAMIC_NONE` motion type and parked obstacle specs.
- Keep moving hurdle, gap, and tilted-pad actor metadata consistent with `dynamic_demo`. For latent-suppressed hurdles and mixed-demo tilted pads, keep the original motion types/specs and use `dynamic_latent_suppressed` rather than changing actor type.
- Preserve gap moving-goal mapping with `dynamic_goal_groups`; static step goals should not be mapped to a moving dynamic group.
- Do not change the dynamic latent schema just to represent the static step. The selected latent group for an inactive/static step should produce invalid or zero dynamic features.
- Do not clear tilted-pad or hurdle actor metadata to remove latent information. `mixed_tilted_pads` should keep the same `DYNAMIC_TILTED_PADS` motion types/specs as the normal generator and suppress latent features by terrain family; `mixed_hurdle`, the hurdle group inside `mixed_demo`, and the tilted-pad groups inside `mixed_demo` should keep their original motion types/specs and suppress latent features with `dynamic_latent_suppressed`.

## Testing

- Cover task registration for `a1_mixed` and verify it maps to `DynamicLeggedRobot`.
- Verify `a1`, `a1_dynamic`, and `a1_mixed` default terrain distributions remain distinct.
- Test `mixed_demo_terrain()` for eight goals, `DYNAMIC_MIXED_DEMO` family id, inactive step actor group, active hurdle/gap/tilted-pad groups, preserved gap goal mapping, and a nonzero static step in the heightfield.
- Test `Terrain.make_terrain()` dispatch with only `mixed_demo` enabled.
- Test `mixed_tilted_pads_terrain()` against `dynamic_tilted_pads_terrain()` with the same random seed; heightfield, goals, motion types, groups, goal mapping, and obstacle specs should match except for family id.
- Test `mixed_hurdle_terrain()` against `dynamic_hurdle_terrain()` with the same random seed; heightfield, goals, motion types, groups, goal mapping, and obstacle specs should match except for family id and latent suppression mask.
- Test that `DynamicLeggedRobot._build_dynamic_env_latent_features()` returns zeros for `DYNAMIC_MIXED_TILTED_PADS`, `DYNAMIC_MIXED_HURDLE`, and hurdle/tilted-pad groups masked inside `DYNAMIC_MIXED_DEMO`, while keeping normal dynamic terrain and mixed-demo gap features nonzero.
- Update `play.py` and `evaluate.py` smoke checks when their task-specific terrain defaults change.

## Cautions

- Do not modify stale copied files under `legged_gym/legged_gym/scripts/legged_gym/` unless runtime inspection proves they are active.
- Do not create a new environment class for `a1_mixed` unless actor runtime requirements genuinely diverge from `DynamicLeggedRobot`.
- Do not let `play.py` hardcoded overrides collapse `a1_mixed` back to the old `a1_dynamic` terrain set.
- When reporting `a1_mixed` results, note that its pure tilted-pad and hurdle terrains no longer expose dynamic obstacle state in env latent despite retaining the same visible/moving obstacle courses; inside `mixed_demo`, hurdle and tilted-pad groups are suppressed but gap latent remains available.
