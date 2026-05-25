#!/usr/bin/env python3
"""Generate top-down atlas images for dynamic terrain suite layouts.

This script does not run Isaac Gym. It only visualizes the data in
dynamic_terrain_suites.py so we can review terrain/task layout design quickly.
"""

import argparse
import importlib.util
import math
import struct
import zlib
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, FancyArrowPatch
except ModuleNotFoundError:
    plt = None
    Rectangle = None
    FancyArrowPatch = None


ROOT = Path(__file__).resolve().parents[1]
SUITE_FILE = ROOT / "legged_gym/legged_gym/utils/dynamic_terrain_suites.py"


COLORS = {
    "moving_hurdle": "tab:red",
    "changing_step_height": "tab:blue",
    "shifting_gap": "tab:green",
    "time_varying_ramp": "tab:purple",
}

RGB_COLORS = {
    "moving_hurdle": (214, 39, 40),
    "changing_step_height": (31, 119, 180),
    "shifting_gap": (44, 160, 44),
    "time_varying_ramp": (148, 103, 189),
}


def load_suites():
    spec = importlib.util.spec_from_file_location(
        "dynamic_terrain_suites_direct", SUITE_FILE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DYNAMIC_TERRAIN_SUITES


def rect_for_obstacle(obs):
    x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])
    size = obs.get("size", [0.5, 0.5, 0.1])
    length = float(size[0])
    width = float(size[1])
    return x - length / 2.0, y - width / 2.0, length, width


def draw_motion_arrow(ax, obs, scale=0.45):
    x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])
    axis = obs.get("motion_axis", "")
    amp = obs.get("amplitude_range", [0.0, 0.0])
    amp_mid = sum(amp) / 2.0 if isinstance(amp, list) and len(amp) == 2 else 0.2
    arrow_len = max(0.15, float(amp_mid) * scale)

    if axis == "x":
        start = (x - arrow_len, y)
        end = (x + arrow_len, y)
    elif axis == "y":
        start = (x, y - arrow_len)
        end = (x, y + arrow_len)
    elif axis == "z":
        ax.text(x, y, "z-motion", ha="center", va="bottom", fontsize=7)
        return
    elif axis == "pitch":
        ax.text(x, y, "pitch", ha="center", va="bottom", fontsize=7)
        return
    else:
        return

    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="<->",
        mutation_scale=10,
        linewidth=1.5,
        color="black",
    )
    ax.add_patch(arrow)


def draw_single_obstacle(ax, obs, index):
    obs_type = obs.get("type", "unknown")
    name = obs.get("name", f"obs_{index}")
    color = COLORS.get(obs_type, "gray")

    if obs_type == "shifting_gap":
        x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])
        size = obs.get("size", [0.08, 1.0, 0.08])
        length = float(size[0])
        width = float(size[1])
        sep = float(obs.get("edge_separation", 0.75))

        gap_clearance = max(0.0, sep - length)
        gap_x0 = x - gap_clearance / 2.0
        gap_y0 = y - width / 2.0
        gap_patch = Rectangle(
            (gap_x0, gap_y0),
            gap_clearance,
            width,
            facecolor="white",
            edgecolor=color,
            hatch="//",
            linewidth=1.2,
            alpha=0.35,
        )
        ax.add_patch(gap_patch)
        if gap_clearance > 0.05:
            ax.text(
                x,
                y - width / 2.0 - 0.08,
                f"gap {gap_clearance:.2f}m",
                ha="center",
                va="top",
                fontsize=7,
                color="black",
            )

        # The two actors are broad takeoff/landing platforms around the gap.
        edge_centers = [(x - sep / 2.0, y), (x + sep / 2.0, y)]
        for edge_id, (ex, ey) in enumerate(edge_centers):
            patch = Rectangle(
                (ex - length / 2.0, ey - width / 2.0),
                length,
                width,
                facecolor=color,
                edgecolor="black",
                alpha=0.55,
            )
            ax.add_patch(patch)
            role = "takeoff" if edge_id == 0 else "landing"
            ax.text(
                ex,
                ey,
                f"{name}\n{role}",
                ha="center",
                va="center",
                fontsize=6,
                color="black",
            )

        draw_motion_arrow(ax, obs)
        return

    x0, y0, length, width = rect_for_obstacle(obs)
    x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])

    patch = Rectangle(
        (x0, y0),
        length,
        width,
        facecolor=color,
        edgecolor="black",
        alpha=0.55,
    )
    ax.add_patch(patch)

    label = f"{name}\n{obs_type}"
    ax.text(x, y, label, ha="center", va="center", fontsize=6, color="black")
    draw_motion_arrow(ax, obs)


def layout_bounds(layout):
    xs = [0.0, 4.5]
    corridor_half_width = float(layout.get("corridor_half_width", 1.0))
    ys = [-corridor_half_width, corridor_half_width]
    for obs in layout.get("obstacles", []):
        x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])
        size = obs.get("size", [0.5, 0.5, 0.1])
        length = float(size[0])
        width = float(size[1])
        if obs.get("type") == "shifting_gap":
            sep = float(obs.get("edge_separation", 0.75))
            half_x = sep / 2.0 + length / 2.0
        else:
            half_x = length / 2.0
        half_y = width / 2.0
        xs.extend([x - half_x, x + half_x])
        ys.extend([y - half_y, y + half_y])
    if layout.get("obstacles"):
        max_obstacle_x = max(
            obs.get("base_position", [0.0, 0.0, 0.0])[0]
            + (
                float(obs.get("edge_separation", 0.0)) / 2.0
                if obs.get("type") == "shifting_gap"
                else 0.0
            )
            + float(obs.get("size", [0.5, 0.5, 0.1])[0]) / 2.0
            for obs in layout["obstacles"]
        )
        xs.append(max_obstacle_x + float(layout.get("runout_length", 0.0)))
    return min(xs), max(xs), min(ys), max(ys)


class RasterCanvas:
    def __init__(self, width, height, bg=(255, 255, 255)):
        self.width = width
        self.height = height
        self.pixels = bytearray(bg * (width * height))

    def blend_pixel(self, x, y, color, alpha=1.0):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        idx = (y * self.width + x) * 3
        inv = 1.0 - alpha
        self.pixels[idx] = int(self.pixels[idx] * inv + color[0] * alpha)
        self.pixels[idx + 1] = int(self.pixels[idx + 1] * inv + color[1] * alpha)
        self.pixels[idx + 2] = int(self.pixels[idx + 2] * inv + color[2] * alpha)

    def rect(self, x0, y0, x1, y1, fill, outline=(0, 0, 0), alpha=1.0):
        left, right = sorted([int(round(x0)), int(round(x1))])
        top, bottom = sorted([int(round(y0)), int(round(y1))])
        left = max(0, left)
        right = min(self.width - 1, right)
        top = max(0, top)
        bottom = min(self.height - 1, bottom)
        for py in range(top, bottom + 1):
            for px in range(left, right + 1):
                self.blend_pixel(px, py, fill, alpha)
        self.line(left, top, right, top, outline)
        self.line(right, top, right, bottom, outline)
        self.line(right, bottom, left, bottom, outline)
        self.line(left, bottom, left, top, outline)

    def line(self, x0, y0, x1, y1, color=(0, 0, 0), alpha=1.0, width=1):
        x0 = int(round(x0))
        y0 = int(round(y0))
        x1 = int(round(x1))
        y1 = int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        radius = max(0, width // 2)
        while True:
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    self.blend_pixel(x0 + ox, y0 + oy, color, alpha)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, radius, fill=(0, 0, 0), alpha=1.0):
        cx = int(round(cx))
        cy = int(round(cy))
        radius = int(round(radius))
        rr = radius * radius
        for py in range(cy - radius, cy + radius + 1):
            for px in range(cx - radius, cx + radius + 1):
                if (px - cx) ** 2 + (py - cy) ** 2 <= rr:
                    self.blend_pixel(px, py, fill, alpha)

    def save_png(self, path):
        def chunk(kind, data):
            payload = kind + data
            return (
                struct.pack(">I", len(data))
                + payload
                + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
            )

        rows = []
        stride = self.width * 3
        for y in range(self.height):
            rows.append(b"\x00" + bytes(self.pixels[y * stride : (y + 1) * stride]))
        data = zlib.compress(b"".join(rows), level=9)
        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(
                b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
            )
            + chunk(b"IDAT", data)
            + chunk(b"IEND", b"")
        )
        path.write_bytes(png)


def draw_raster_arrow(canvas, transform, obs, scale=0.45):
    x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])
    axis = obs.get("motion_axis", "")
    amp = obs.get("amplitude_range", [0.0, 0.0])
    amp_mid = sum(amp) / 2.0 if isinstance(amp, list) and len(amp) == 2 else 0.2
    arrow_len = max(0.15, float(amp_mid) * scale)

    if axis == "x":
        start = transform(x - arrow_len, y)
        end = transform(x + arrow_len, y)
    elif axis == "y":
        start = transform(x, y - arrow_len)
        end = transform(x, y + arrow_len)
    elif axis == "pitch":
        start = transform(x - 0.16, y - 0.16)
        end = transform(x + 0.16, y + 0.16)
    else:
        return

    canvas.line(*start, *end, color=(0, 0, 0), width=2)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    for point, direction in [(end, angle), (start, angle + math.pi)]:
        for offset in [2.5, -2.5]:
            head_angle = direction + offset
            hx = point[0] - 10 * math.cos(head_angle)
            hy = point[1] - 10 * math.sin(head_angle)
            canvas.line(point[0], point[1], hx, hy, color=(0, 0, 0), width=2)


def draw_raster_layout(layout, out_path):
    width, height = 1440, 810
    margin_x, margin_y = 95, 90
    min_x, max_x, min_y, max_y = layout_bounds(layout)
    x_left = min(-0.5, min_x - 0.35)
    x_right = max(4.8, max_x + 0.35)
    y_bottom = min(-1.4, min_y - 0.25)
    y_top = max(1.4, max_y + 0.25)
    scale_x = (width - 2 * margin_x) / (x_right - x_left)
    scale_y = (height - 2 * margin_y) / (y_top - y_bottom)
    scale = min(scale_x, scale_y)

    def transform(x, y):
        px = margin_x + (x - x_left) * scale
        py = height - margin_y - (y - y_bottom) * scale
        return px, py

    canvas = RasterCanvas(width, height)
    corridor_half_width = float(layout.get("corridor_half_width", 0.65))
    cx0, cy0 = transform(0.0, -corridor_half_width)
    cx1, cy1 = transform(x_right - 0.3, corridor_half_width)
    canvas.rect(
        cx0, cy0, cx1, cy1, fill=(245, 248, 242), outline=(190, 205, 180), alpha=1.0
    )

    for gx in [x_left + i * 0.5 for i in range(int((x_right - x_left) / 0.5) + 2)]:
        x0, y0 = transform(gx, y_bottom)
        x1, y1 = transform(gx, y_top)
        canvas.line(x0, y0, x1, y1, color=(225, 225, 225))
    for gy in [y_bottom + i * 0.5 for i in range(int((y_top - y_bottom) / 0.5) + 2)]:
        x0, y0 = transform(x_left, gy)
        x1, y1 = transform(x_right, gy)
        canvas.line(x0, y0, x1, y1, color=(225, 225, 225))

    start = transform(0.0, 0.0)
    end = transform(x_right - 0.3, 0.0)
    dash = 18
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = max(1.0, math.hypot(dx, dy))
    steps = int(dist // dash)
    for i in range(0, steps, 2):
        a = i / steps
        b = min(1.0, (i + 1) / steps)
        canvas.line(
            start[0] + dx * a,
            start[1] + dy * a,
            start[0] + dx * b,
            start[1] + dy * b,
            color=(140, 140, 140),
        )
    canvas.circle(*start, radius=13, fill=(0, 0, 0))

    for obs in layout.get("obstacles", []):
        obs_type = obs.get("type", "unknown")
        color = RGB_COLORS.get(obs_type, (128, 128, 128))
        x, y, _z = obs.get("base_position", [0.0, 0.0, 0.0])
        size = obs.get("size", [0.5, 0.5, 0.1])
        length = float(size[0])
        width_m = float(size[1])

        if obs_type == "shifting_gap":
            sep = float(obs.get("edge_separation", 0.75))
            gap_clearance = max(0.0, sep - length)
            gx0, gy0 = transform(x - gap_clearance / 2.0, y - width_m / 2.0)
            gx1, gy1 = transform(x + gap_clearance / 2.0, y + width_m / 2.0)
            canvas.rect(
                gx0, gy0, gx1, gy1, fill=(255, 255, 255), outline=color, alpha=1.0
            )
            left, right = sorted([int(round(gx0)), int(round(gx1))])
            top, bottom = sorted([int(round(gy0)), int(round(gy1))])
            height_px = bottom - top
            for hx in range(left - height_px, right + 1, 18):
                for step_px in range(height_px + 1):
                    px = hx + step_px
                    py = bottom - step_px
                    if left <= px <= right and top <= py <= bottom:
                        canvas.blend_pixel(px, py, color, alpha=0.45)
            centers = [(x - sep / 2.0, y), (x + sep / 2.0, y)]
            for cx, cy in centers:
                x0, y0 = transform(cx - length / 2.0, cy - width_m / 2.0)
                x1, y1 = transform(cx + length / 2.0, cy + width_m / 2.0)
                canvas.rect(x0, y0, x1, y1, fill=color, outline=(0, 0, 0), alpha=0.55)
            draw_raster_arrow(canvas, transform, obs)
            continue

        x0, y0 = transform(x - length / 2.0, y - width_m / 2.0)
        x1, y1 = transform(x + length / 2.0, y + width_m / 2.0)
        canvas.rect(x0, y0, x1, y1, fill=color, outline=(0, 0, 0), alpha=0.55)
        draw_raster_arrow(canvas, transform, obs)

    canvas.save_png(out_path)


def plot_layout(suite_name, layout_id, layout, out_path):
    if plt is None:
        draw_raster_layout(layout, out_path)
        return

    fig, ax = plt.subplots(figsize=(8, 4.5))

    difficulty = layout.get("difficulty")
    difficulty_suffix = f" ({difficulty})" if difficulty else ""
    ax.set_title(
        f"{suite_name} / layout {layout_id}: {layout.get('name')}{difficulty_suffix}"
    )
    ax.set_xlabel("x: forward direction")
    ax.set_ylabel("y: lateral direction")

    # Robot start marker.
    ax.scatter([0.0], [0.0], marker="o", s=80, color="black")
    ax.text(0.0, 0.08, "robot start", ha="center", fontsize=8)

    min_x, max_x, min_y, max_y = layout_bounds(layout)
    x_left = min(-0.5, min_x - 0.35)
    x_right = max(4.8, max_x + 0.35)
    y_bottom = min(-1.4, min_y - 0.25)
    y_top = max(1.4, max_y + 0.25)

    corridor_half_width = float(layout.get("corridor_half_width", 0.65))
    ax.axhspan(
        -corridor_half_width,
        corridor_half_width,
        xmin=0.0,
        xmax=1.0,
        facecolor="tab:green",
        alpha=0.08,
        edgecolor="tab:green",
        linewidth=1.0,
    )

    # Draw a nominal route centerline.
    ax.plot([0.0, x_right - 0.3], [0.0, 0.0], linestyle="--", linewidth=1, color="gray")

    for i, obs in enumerate(layout.get("obstacles", [])):
        draw_single_obstacle(ax, obs, i)

    ax.set_xlim(x_left, x_right)
    ax.set_ylim(y_bottom, y_top)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)

    # Legend-like text.
    ax.text(
        4.75,
        -1.35,
        "red=hurdle, blue=step, green=gap platforms, purple=ramp",
        ha="right",
        va="bottom",
        fontsize=7,
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def write_markdown_index(suites, out_dir):
    md_path = out_dir / "README.md"
    lines = [
        "# Dynamic Terrain Layout Atlas",
        "",
        "This atlas is generated from `dynamic_terrain_suites.py`.",
        "It is a top-down design preview, not an Isaac Gym render.",
        "",
        "Color meaning:",
        "",
        "- Red: moving hurdle",
        "- Blue: changing step height",
        "- Green: shifting gap takeoff/landing platforms",
        "- Purple: time-varying ramp",
        "",
    ]

    for suite_name, layouts in suites.items():
        lines.append(f"## {suite_name}")
        lines.append("")
        for layout_id, layout in enumerate(layouts):
            img = f"{suite_name}_layout_{layout_id}.png"
            difficulty = layout.get("difficulty", "unspecified")
            lines.append(
                f"### Layout {layout_id}: `{layout.get('name')}` ({difficulty})"
            )
            lines.append("")
            lines.append(f"![{suite_name} layout {layout_id}]({img})")
            lines.append("")
            lines.append(
                f"Metadata: runup={layout.get('runup_length', 'n/a')}, "
                f"runout={layout.get('runout_length', 'n/a')}, "
                f"corridor_half_width={layout.get('corridor_half_width', 'n/a')}"
            )
            lines.append("")
            lines.append("| obstacle | type | base_position | size | motion |")
            lines.append("|---|---|---|---|---|")
            for obs in layout.get("obstacles", []):
                motion = (
                    f"axis={obs.get('motion_axis')}, "
                    f"amp={obs.get('amplitude_range')}, "
                    f"freq={obs.get('frequency_range')}"
                )
                lines.append(
                    f"| `{obs.get('name')}` | `{obs.get('type')}` | "
                    f"`{obs.get('base_position')}` | `{obs.get('size')}` | `{motion}` |"
                )
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out_dir",
        default="terrain_layout_atlas",
        help="Output directory for generated PNGs and README.md.",
    )
    parser.add_argument(
        "--suite",
        default=None,
        help="Optional suite name to plot only one suite.",
    )
    args = parser.parse_args()

    suites = load_suites()
    if args.suite is not None:
        if args.suite not in suites:
            raise SystemExit(f"Unknown suite: {args.suite}. Available: {list(suites)}")
        suites = {args.suite: suites[args.suite]}

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for suite_name, layouts in suites.items():
        for layout_id, layout in enumerate(layouts):
            out_path = out_dir / f"{suite_name}_layout_{layout_id}.png"
            plot_layout(suite_name, layout_id, layout, out_path)
            print(f"Wrote {out_path}")

    md_path = write_markdown_index(suites, out_dir)
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
