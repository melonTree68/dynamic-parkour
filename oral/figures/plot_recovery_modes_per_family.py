from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_utils import apply_style, read_metrics, save_pdf, terrain_family


OUT = Path(__file__).with_name("recovery_modes_per_family.pdf")

RUNS = {
    "ROA": {
        "path": "legged_gym/logs/augment-latent-roa-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#ff7f0e",
    },
    "teacher-student": {
        "path": "legged_gym/logs/augment-latent-ts-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#9467bd",
    },
}

FAMILIES = [
    ("dynamic_hurdle", "hurdle"),
    ("dynamic_gap", "gap"),
    ("dynamic_tilted_pads", "tilted"),
    ("dynamic_step", "step"),
    ("dynamic_demo", "demo"),
]


apply_style()
labels = [short for _family, short in FAMILIES]
x = np.arange(len(labels))
width = 0.36

plt.figure(figsize=(7.0, 3.6))
for idx, (label, spec) in enumerate(RUNS.items()):
    df = read_metrics(spec["path"])
    df = df.assign(family=df["eval_terrain"].apply(terrain_family))
    values = []
    for family, _short in FAMILIES:
        fam = df[df["family"] == family]
        values.append(float(fam["num_waypoints_mean"].max()) if not fam.empty else 0.0)
    plt.bar(x + (idx - 0.5) * width, values, width=width, color=spec["color"], label=label)

plt.xticks(x, labels)
plt.ylabel("best mean waypoints")
plt.ylim(0.0, 1.0)
plt.legend(loc="upper right")
save_pdf(OUT)
