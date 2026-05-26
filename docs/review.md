# Dynamic Terrain Review

## Not Minimal / Needs Simplification

- The docs are stale: `docs/tune.md` describes `gap_motion="overlap_width"`, while the implementation supports `"width"` or `"translate"`.

## Design Gaps

The number of obstacle sets satisfies the requested coverage, but the complete dynamic-terrain behavior is not finished:

- Suite `goals` are only printed/drawn by the viewer; training still follows static terrain goals from `legged_gym/legged_gym/envs/base/legged_robot.py`.
- Several generated gap/mixed waypoint sequences go backward in `x`, so they are not ready to become navigation goals.
- Height observations still sample the static terrain mesh only (`legged_gym/legged_gym/envs/base/legged_robot.py`); moving actors are invisible to terrain scans.
- A "dynamic gap" is currently two moving raised actors over unchanged static terrain, not an actual moving hole. Registered dynamic tasks also retain the original static terrain mixture, so suite actors are overlaid on unrelated static courses.
