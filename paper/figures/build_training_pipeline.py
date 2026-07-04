from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


HERE = Path(__file__).resolve().parent
FRAMES = HERE / "training_pipeline_frames"
OUT = HERE / "training_pipeline_ai.png"

W, H = 2400, 920
PANEL_Y = 145
PANEL_H = 610
RADIUS = 28


def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size, index=1 if bold else 0)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(44, bold=True)
F_ARROW = font(30, bold=True)
F_LABEL = font(24, bold=True)
F_SMALL = font(21, bold=False)


def crop_sim_frame(path):
    img = Image.open(path).convert("RGB")
    # Demo frames have a large black sky; keep enough horizon for context while
    # dedicating most space to the terrain and obstacle actor.
    return img.crop((0, 115, img.width, img.height))


def fit_cover(img, size):
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.55))


def rounded_panel(draw, box, outline):
    x, y, w, h = box
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=RADIUS,
        fill=(248, 249, 250),
        outline=outline,
        width=4,
    )


def paste_rounded(canvas, img, box, radius=RADIUS - 4):
    x, y, w, h = box
    fitted = fit_cover(img, (w, h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    canvas.paste(fitted, (x, y), mask)


def draw_text_center(draw, x, y, text, fnt, fill=(25, 28, 33)):
    bbox = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=5, align="center")
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.multiline_text((x - w / 2, y - h / 2), text, font=fnt, fill=fill, spacing=5, align="center")


def draw_label(draw, xy, text, fill=(255, 255, 255), bg=(0, 0, 0, 170)):
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=F_SMALL)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    pad_x, pad_y = 9, 6
    draw.rounded_rectangle(
        [x, y, x + w + 2 * pad_x, y + h + 2 * pad_y],
        radius=9,
        fill=bg,
    )
    draw.text((x + pad_x, y + pad_y), text, font=F_SMALL, fill=fill)


def arrow(draw, start, end, color=(35, 94, 184), width=7):
    sx, sy = start
    ex, ey = end
    draw.line([start, end], fill=color, width=width)
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head, wing = 28, 14
    pts = [
        (ex, ey),
        (ex - ux * head + px * wing, ey - uy * head + py * wing),
        (ex - ux * head - px * wing, ey - uy * head - py * wing),
    ]
    draw.polygon(pts, fill=color)


def block(draw, xy, wh, text, outline, fill=(255, 255, 255), fnt=F_SMALL):
    x, y = xy
    w, h = wh
    draw.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill, outline=outline, width=3)
    draw_text_center(draw, x + w / 2, y + h / 2, text, fnt, fill=(20, 24, 30))


def draw_network(draw, x, y, color):
    # Simple deterministic encoder / actor glyphs.
    for i in range(4):
        h = 150 - i * 22
        draw.rounded_rectangle(
            [x + i * 18, y + 75 - h / 2, x + 42 + i * 18, y + 75 + h / 2],
            radius=8,
            fill=color,
            outline=(40, 58, 80),
            width=2,
        )


def build_dynamic_panel(canvas, draw, box):
    x, y, w, h = box
    pad = 18
    gutter = 12
    cell_w = (w - 2 * pad - gutter) // 2
    cell_h = (h - 2 * pad - gutter) // 2
    entries = [
        ("dynamic_hurdle.png", "hurdle"),
        ("dynamic_gap.png", "gap"),
        ("dynamic_tilted_pad.png", "tilted pad"),
        ("dynamic_step.png", "step"),
    ]
    for idx, (name, label) in enumerate(entries):
        cx = x + pad + (idx % 2) * (cell_w + gutter)
        cy = y + pad + (idx // 2) * (cell_h + gutter)
        frame = crop_sim_frame(FRAMES / name)
        paste_rounded(canvas, frame, (cx, cy, cell_w, cell_h), radius=16)
        draw.rounded_rectangle([cx, cy, cx + cell_w, cy + cell_h], radius=16, outline=(230, 235, 240), width=2)
        draw_label(draw, (cx + 12, cy + cell_h - 45), label)


def build_latent_panel(canvas, draw, box):
    x, y, w, h = box
    pad = 22
    left_w = 245
    top = crop_sim_frame(FRAMES / "teacher_frame.png")
    bottom = crop_sim_frame(FRAMES / "student_frame.png")
    paste_rounded(canvas, top, (x + pad, y + 44, left_w, 215), radius=16)
    paste_rounded(canvas, bottom, (x + pad, y + h - 259, left_w, 215), radius=16)
    draw_label(draw, (x + pad + 12, y + 54), "teacher rollout", bg=(18, 52, 94, 185))
    draw_label(draw, (x + pad + 12, y + h - 249), "depth rollout", bg=(18, 52, 94, 185))

    cx = x + pad + left_w + 56
    top_y = y + 70
    bot_y = y + h - 235

    draw_network(draw, cx, top_y + 76, (91, 150, 222))
    block(draw, (cx + 115, top_y + 40), (130, 72), "ROA\nhistory", (91, 150, 222), fill=(235, 244, 255), fnt=F_SMALL)
    block(draw, (cx + 285, top_y + 40), (128, 72), "teacher\npolicy", (220, 131, 39), fill=(255, 244, 232), fnt=F_SMALL)

    draw_network(draw, cx, bot_y + 76, (91, 150, 222))
    block(draw, (cx + 115, bot_y + 30), (130, 94), "teacher-\nstudent\nenv latent", (116, 82, 190), fill=(244, 239, 255), fnt=F_SMALL)
    block(draw, (cx + 285, bot_y + 40), (128, 72), "student\npolicy", (220, 131, 39), fill=(255, 244, 232), fnt=F_SMALL)

    arrow(draw, (x + pad + left_w + 8, y + 150), (cx - 12, y + 150), color=(70, 92, 120), width=5)
    arrow(draw, (cx + 78, y + 150), (cx + 112, y + 150), color=(70, 92, 120), width=5)
    arrow(draw, (cx + 248, y + 150), (cx + 280, y + 150), color=(70, 92, 120), width=5)
    arrow(draw, (x + pad + left_w + 8, y + h - 150), (cx - 12, y + h - 150), color=(70, 92, 120), width=5)
    arrow(draw, (cx + 78, y + h - 150), (cx + 112, y + h - 150), color=(70, 92, 120), width=5)
    arrow(draw, (cx + 248, y + h - 150), (cx + 280, y + h - 150), color=(70, 92, 120), width=5)

    # Supervision and shared recovered latent path.
    arrow(draw, (cx + 350, y + 190), (cx + 350, y + h - 190), color=(220, 131, 39), width=5)
    draw_text_center(draw, cx + 430, y + h / 2, "action\nsupervision", F_SMALL, fill=(108, 62, 16))
    arrow(draw, (cx + 180, y + 230), (cx + 180, y + h - 215), color=(116, 82, 190), width=5)
    draw_text_center(draw, cx + 160, y + h / 2, "recovered\nenv latent", F_SMALL, fill=(80, 49, 150))


def main():
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    panels = [
        (70, PANEL_Y, 620, PANEL_H),
        (820, PANEL_Y, 620, PANEL_H),
        (1570, PANEL_Y, 760, PANEL_H),
    ]
    titles = [
        "1  Static expert",
        "2  Dynamic-obstacle task",
        "3  Latent recovery + depth student",
    ]
    outlines = [(45, 96, 180), (37, 138, 71), (118, 73, 190)]

    for box, title, color in zip(panels, titles, outlines):
        x, y, w, h = box
        draw_text_center(draw, x + w / 2, 70, title, F_TITLE)
        rounded_panel(draw, box, color)

    paste_rounded(canvas, crop_sim_frame(FRAMES / "static_demo.png"), panels[0])
    build_dynamic_panel(canvas, draw, panels[1])
    build_latent_panel(canvas, draw, panels[2])

    # Arrows live in the whitespace between rounded frames.
    arrow(draw, (710, PANEL_Y + PANEL_H / 2), (800, PANEL_Y + PANEL_H / 2), color=(45, 96, 180), width=8)
    draw_text_center(draw, 755, PANEL_Y + PANEL_H / 2 - 58, "DAgger\nimitation", F_ARROW, fill=(45, 96, 180))
    arrow(draw, (1460, PANEL_Y + PANEL_H / 2), (1550, PANEL_Y + PANEL_H / 2), color=(37, 138, 71), width=8)
    draw_text_center(draw, 1505, PANEL_Y + PANEL_H / 2 - 58, "Camera\ndistillation", F_ARROW, fill=(37, 138, 71))

    canvas.convert("RGB").save(OUT, quality=96)


if __name__ == "__main__":
    main()
