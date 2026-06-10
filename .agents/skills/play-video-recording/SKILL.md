---
name: play-video-recording
description: Use when adding, debugging, or running `play.py` video recording for extreme-parkour, including per-environment Isaac Gym camera sensors, MP4 output under `videos/{proj_name}/{exptid}/`, camera follow modes, and recording CLI options.
---

# Play Video Recording

## Overview

`legged_gym/legged_gym/scripts/play.py` can record one MP4 per simulated environment instance. Each video corresponds to one terrain+robot instance and concatenates the requested number of episodes.

Videos are written to:

```text
videos/{proj_name}/{exptid}/{timestamp}/env_000.mp4
```

## CLI

Enable recording with `--record_video`.

Main options:

- `--video_episodes`: number of episodes concatenated into each env video, default `1`.
- `--video_episode_timeout_s`: recording episode timeout, default `20.0`.
- `--video_width`, `--video_height`, `--video_fps`: camera/video settings.
- `--video_camera_mode`: `yaw` or `attached`, default `yaw`.
- `--video_camera_pos`: camera offset as `x,y,z` in robot coordinates, default rear view.
- `--video_camera_target`: yaw-mode look-at offset as `x,y,z` in robot coordinates.
- `--video_camera_pitch_deg`: attached-mode pitch angle.

## Design Decisions

- Recording is opt-in; normal `play.py` behavior should stay unchanged when `--record_video` is absent.
- `yaw` mode is the default because it follows robot heading without inheriting roll/pitch, producing steadier inspection videos.
- `attached` mode attaches an Isaac Gym camera to the robot root rigid body with `FOLLOW_TRANSFORM`, producing a literal body-mounted view.
- Output uses OpenCV `VideoWriter` with the `mp4v` codec. `cv2` and `imageio` are available in the `parkour` conda environment.
- Recording requires graphics. Do not combine `--record_video` with `--headless`.

## Implementation Notes

- Create recording camera sensors after `task_registry.make_env(...)`, one per `env.envs[i]`.
- Use `gym.get_camera_image(..., gymapi.IMAGE_COLOR)` and convert RGBA frames to BGR before writing with OpenCV.
- Record only envs whose completed episode count is below `--video_episodes`.
- Count completed episodes from the `dones` tensor returned by `env.step(...)`.
- Release all `VideoWriter` handles in a `finally` block so interrupted recordings finalize cleanly.

## Verification

Use `compileall` for a cheap syntax check after edits to `play.py` or CLI parsing.

For a smoke run, use a small timeout and resolution, for example:

```bash
python legged_gym/legged_gym/scripts/play.py --record_video --video_episodes 1 --video_episode_timeout_s 1 --video_width 320 --video_height 180
```

Then verify MP4 files exist under `videos/{proj_name}/{exptid}/{timestamp}/` and can be opened by OpenCV.
