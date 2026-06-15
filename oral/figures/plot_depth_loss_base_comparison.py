from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import aggregate_by_checkpoint, apply_style, read_metrics, save_pdf, smooth


OUT = Path(__file__).with_name("depth_loss_base_comparison.pdf")
WINDOW = 5

RUNS = {
    "pure ROA": {
        "path": "legged_gym/logs/augment-latent-roa-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#ff7f0e",
    },
    "pure teacher-student": {
        "path": "legged_gym/logs/augment-latent-ts-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#9467bd",
    },
}


apply_style()
plt.figure(figsize=(7.0, 3.6))
for label, spec in RUNS.items():
    df = aggregate_by_checkpoint(read_metrics(spec["path"]))
    plt.plot(
        df["checkpoint"],
        smooth(df["num_waypoints_mean"], WINDOW),
        lw=2.2,
        color=spec["color"],
        label=label,
    )

plt.xlabel("base-RL iteration")
plt.ylabel("mean waypoints")
plt.ylim(0.0, 0.9)
plt.legend(loc="lower right")
save_pdf(OUT)
