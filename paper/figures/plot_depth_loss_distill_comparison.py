from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import (
    aggregate_by_checkpoint,
    apply_style,
    best_waypoint_before,
    keep_until,
    read_metrics,
    save_pdf,
    smooth,
)


OUT = Path(__file__).with_name("depth_loss_distill_comparison.pdf")
WINDOW = 5
MAX_CHECKPOINT = 20000

RUNS = {
    "hybrid": {
        "distill": "legged_gym/logs/augment-latent-hybrid-mixed-terrain/distill-from-resume-from-imitate-base-15k-100-20k/metrics.csv",
        "base": "legged_gym/logs/augment-latent-hybrid-mixed-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#d62728",
    },
    "hybrid + depth encoder loss": {
        "distill": "legged_gym/logs/augment-latent-hybrid-mixed-terrain/distill-from-resume-from-imitate-base-15k-100-20k-depth-enc-loss/metrics.csv",
        "base": "legged_gym/logs/augment-latent-hybrid-mixed-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#17becf",
    },
}


apply_style()
plt.figure(figsize=(7.0, 3.6))
for label, spec in RUNS.items():
    df = keep_until(aggregate_by_checkpoint(read_metrics(spec["distill"])), MAX_CHECKPOINT)
    color = spec["color"]
    plt.plot(
        df["checkpoint"],
        smooth(df["num_waypoints_mean"], WINDOW),
        lw=2.2,
        color=color,
        label=label,
    )
    plt.axhline(
        best_waypoint_before(spec["base"], 20000),
        color=color,
        lw=1.4,
        ls="--",
        alpha=0.75,
    )

plt.xlabel("distillation iteration")
plt.ylabel("mean waypoints")
plt.ylim(0.0, 1.05)
plt.legend(loc="lower right")
save_pdf(OUT)
