from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


HERE = Path(__file__).resolve().parent
FRAMES = HERE / "training_pipeline_frames"
ASSETS = HERE / "training_pipeline_assets"
OUT = HERE / "training_pipeline_ai.png"

W, H = 2700, 920
PANEL_Y = 145
PANEL_H = 610
RADIUS = 28
LABEL_BG = (18, 52, 94, 185)


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
F_BLOCK = font(25, bold=False)


def crop_sim_frame(path):
    img = Image.open(path).convert("RGB")
    # Keep the demo viewpoint but remove empty simulator sky so the obstacles
    # remain legible after the paper scales the figure down.
    top = min(70, img.height // 4)
    return img.crop((0, top, img.width, img.height))


def fit_cover(img, size):
    return ImageOps.fit(img, size, method=Image.Resampling.BICUBIC, centering=(0.5, 0.62))


def prepare_frame(img):
    img = ImageOps.autocontrast(img, cutoff=1)
    return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=150, threshold=3))


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
    fitted = fit_cover(prepare_frame(img), (w, h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    canvas.paste(fitted, (x, y), mask)


def paste_contain(canvas, img, box):
    x, y, w, h = box
    src = img.convert("RGBA")
    bbox = src.getbbox()
    if bbox:
        src = src.crop(bbox)
    src.thumbnail((w, h), Image.Resampling.LANCZOS)
    px = x + (w - src.width) // 2
    py = y + (h - src.height) // 2
    canvas.paste(src, (px, py), src)


def draw_text_center(draw, x, y, text, fnt, fill=(25, 28, 33)):
    bbox = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=5, align="center")
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.multiline_text((x - w / 2, y - h / 2), text, font=fnt, fill=fill, spacing=5, align="center")


def draw_label(draw, xy, text, fill=(255, 255, 255), bg=LABEL_BG):
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
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head, wing = 30, 15
    base = (ex - ux * head, ey - uy * head)
    draw.line([start, base], fill=color, width=width)
    pts = [
        (ex, ey),
        (base[0] + px * wing, base[1] + py * wing),
        (base[0] - px * wing, base[1] - py * wing),
    ]
    draw.polygon(pts, fill=color)


def thin_arrow(draw, start, end, color=(65, 82, 105), width=4):
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    length = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head, wing = 20, 10
    base = (ex - ux * head, ey - uy * head)
    draw.line([start, base], fill=color, width=width)
    draw.polygon(
        [
            (ex, ey),
            (base[0] + px * wing, base[1] + py * wing),
            (base[0] - px * wing, base[1] - py * wing),
        ],
        fill=color,
    )


def block(draw, xy, wh, text, outline, fill=(255, 255, 255), fnt=F_SMALL):
    x, y = xy
    w, h = wh
    draw.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=fill, outline=outline, width=3)
    draw_text_center(draw, x + w / 2, y + h / 2, text, fnt, fill=(20, 24, 30))


def draw_network(canvas, x, y):
    block_img = Image.open(ASSETS / "mlp_icon_original.png")
    paste_contain(canvas, block_img, (x, y, 118, 118))


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
    pad = 24
    left_w = 270
    top = crop_sim_frame(FRAMES / "teacher_frame.png")
    bottom = Image.open(ASSETS / "depth_rollout_ai.png").convert("RGB")
    top_box = (x + pad, y + 48, left_w, 212)
    bot_box = (x + pad, y + h - 260, left_w, 212)
    paste_rounded(canvas, top, top_box, radius=16)
    paste_rounded(canvas, bottom, bot_box, radius=16)
    draw_label(draw, (x + pad + 12, y + 58), "teacher rollout")
    draw_label(draw, (x + pad + 12, y + h - 250), "depth rollout")

    row_top = y + 154
    row_bot = y + h - 154
    mlp_x = x + pad + left_w + 58
    mlp_w = 118
    roa_x, roa_w, roa_h = mlp_x + 158, 170, 88
    policy_x, policy_w, policy_h = roa_x + 220, 164, 88
    env_w, env_h = 182, 118

    draw_network(canvas, mlp_x, row_top - 59)
    block(draw, (roa_x, row_top - roa_h / 2), (roa_w, roa_h), "ROA\nhistory", (91, 150, 222), fill=(235, 244, 255), fnt=F_BLOCK)
    block(draw, (policy_x, row_top - policy_h / 2), (policy_w, policy_h), "teacher\npolicy", (220, 131, 39), fill=(255, 244, 232), fnt=F_BLOCK)

    draw_network(canvas, mlp_x, row_bot - 59)
    block(draw, (roa_x - 6, row_bot - env_h / 2), (env_w, env_h), "teacher-\nstudent\nenv latent", (116, 82, 190), fill=(244, 239, 255), fnt=F_BLOCK)
    block(draw, (policy_x, row_bot - policy_h / 2), (policy_w, policy_h), "student\npolicy", (220, 131, 39), fill=(255, 244, 232), fnt=F_BLOCK)

    # Clean horizontal arrows between components.
    frame_right = x + pad + left_w
    thin_arrow(draw, (frame_right + 14, row_top), (mlp_x - 12, row_top))
    thin_arrow(draw, (mlp_x + mlp_w + 12, row_top), (roa_x - 12, row_top))
    thin_arrow(draw, (roa_x + roa_w + 12, row_top), (policy_x - 12, row_top))
    thin_arrow(draw, (frame_right + 14, row_bot), (mlp_x - 12, row_bot))
    thin_arrow(draw, (mlp_x + mlp_w + 12, row_bot), (roa_x - 18, row_bot))
    thin_arrow(draw, (roa_x - 6 + env_w + 12, row_bot), (policy_x - 12, row_bot))

    # Vertical supervision paths; labels are placed consistently to the left.
    latent_x = roa_x + roa_w / 2
    action_x = policy_x + policy_w / 2
    arrow(draw, (latent_x, row_top + roa_h / 2 + 26), (latent_x, row_bot - env_h / 2 - 16), color=(116, 82, 190), width=5)
    draw_text_center(draw, latent_x - 72, (row_top + row_bot) / 2, "recovered\nenv latent", F_SMALL, fill=(80, 49, 150))
    arrow(draw, (action_x, row_top + policy_h / 2 + 26), (action_x, row_bot - policy_h / 2 - 16), color=(220, 131, 39), width=5)
    draw_text_center(draw, action_x - 82, (row_top + row_bot) / 2, "action\nsupervision", F_SMALL, fill=(108, 62, 16))


def main():
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    panels = [
        (60, PANEL_Y, 590, PANEL_H),
        (870, PANEL_Y, 590, PANEL_H),
        (1680, PANEL_Y, 960, PANEL_H),
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
    arrow(draw, (690, PANEL_Y + PANEL_H / 2), (830, PANEL_Y + PANEL_H / 2), color=(45, 96, 180), width=8)
    draw_text_center(draw, 760, PANEL_Y + PANEL_H / 2 - 58, "DAgger\nimitation", F_ARROW, fill=(45, 96, 180))
    arrow(draw, (1500, PANEL_Y + PANEL_H / 2), (1640, PANEL_Y + PANEL_H / 2), color=(37, 138, 71), width=8)
    draw_text_center(draw, 1570, PANEL_Y + PANEL_H / 2 - 58, "Camera\ndistillation", F_ARROW, fill=(37, 138, 71))

    canvas.convert("RGB").save(OUT, quality=96)


if __name__ == "__main__":
    main()
