# Original Terrain Design Notes

The original Extreme Parkour terrain atlas presents each cell as a short forward
course segment rather than an isolated obstacle demo. The repeated pattern is a
clear run-up, a dense obstacle region, and a landing or runout region inside a
valid corridor. Difficulty changes across rows by increasing obstacle size,
spacing, count, staggering, and combinations while preserving a readable route.

The previous dynamic suite layouts used the same actor primitives, but many
layouts were still visually sparse: single hurdles, single steps, marker-like
gap edges, and mixed layouts that felt like unrelated placements. That made the
suite useful for primitive validation, but less representative of the original
task-level terrain style.

The revised dynamic suites keep the actor-only implementation and static
heightfield/trimesh assumption. Each layout now carries lightweight design
metadata (`difficulty`, `runup_length`, `runout_length`, and
`corridor_half_width`) and follows an easy-to-hard sequence within the pure
suites:

- `pure_hurdle`: thin-x, wide-y barriers arranged as a single hurdle, double
  hurdle, staggered hurdles, and a multi-hurdle short course.
- `pure_step`: progressive two-level, three-step, offset staircase, and
  increasing platform-sequence layouts.
- `pure_gap`: thick takeoff/landing platform actors with visible gap clearance,
  progressing from short to medium to wide and repeated staggered gaps.
- `pure_ramp`: long, wide, thin pitch-rotating boxes for soft, steep, reverse,
  and paired ramp courses.
- `mixed`: short sequential courses that combine primitives as
  hurdle -> step -> ramp, gap -> landing step -> ramp, and
  hurdle -> gap -> staircase -> ramp.

This preserves primitive mode, suite mode, and the disabled-by-default dynamic
obstacle configuration while making the atlas read more like the original
course-based terrain design.

The follow-up micro-revision further densifies the course layouts most visible
in the atlas: `pure_gap` now progresses from one platform gap to repeated
multi-gap courses, `pure_ramp` progresses from one long ramp to multi-ramp
sequences, and the hardest mixed layout combines hurdle, gap, step, and ramp
sequences into one longer short-course segment.

Each dynamic suite layout now also defines explicit local `goals` that follow
the intended route through the actor course. The atlas renders these as ordered
red waypoints, and the dynamic terrain viewer suppresses original static
terrain goals by default in suite mode so those legacy markers do not conflict
with the dynamic course path.
