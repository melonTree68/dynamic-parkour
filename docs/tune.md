# Dynamic Terrain Tuning

Dynamic terrain suite layouts live in
`legged_gym/legged_gym/utils/dynamic_terrain_suites.py`. 

- Hurdles: tune travel with `amplitude_range` and speed with
  `frequency_range` in `hurdle(...)`.
- Steps: tune visible height change with `amplitude_range` in `step(...)`.
  `step_height`/`height` controls the block height; `emerges_from_ground`
  keeps the visual motion as a rising/falling step.
- Gaps: suite gaps use `gap_motion="overlap_width"`. Each side expands into a
  fixed block plus a moving block; tune visible gap-width change with
  `amplitude_range`, `edge_separation`, and block `length`.
- Ramps: suite ramps default to `axis="roll"`, rotating around the forward x
  axis. Tune tilt with `amplitude_range`, `frequency_range`, and per-ramp
  `phase_range`; use different phase ranges for multiple ramps in one layout.
- Same-type consistency: `_apply_layout_motion_consistency()` copies the first
  obstacle's amplitude/frequency range to later obstacles of the same type in a
  layout. Keep the first obstacle of each type as the intended layout setting.
- Mixed course lengths: keep mixed obstacles roughly inside the same x span,
  currently about x=1.0 to x=7.0, with hurdle/gap/step/ramp sections balanced.

