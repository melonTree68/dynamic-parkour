from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import (
    aggregate_by_checkpoint,
    apply_style,
    best_value,
    keep_until,
    read_metrics,
    save_pdf,
    smooth,
)


OUT = Path(__file__).with_name("distillation_waypoints.pdf")
WINDOW = 5
MAX_CHECKPOINT = 21000

RUNS = {
    "original static distill": {
        "distill": "legged_gym/logs/original-pipeline-static-terrain/distill-from-15k/metrics.csv",
        "base": "legged_gym/logs/original-pipeline-static-terrain/base/metrics.csv",
        "color": "#1f77b4",
    },
    "original dynamic distill": {
        "distill": "legged_gym/logs/original-pipeline-dynamic-terrain/distill-from-15k-v2-16f4736/metrics.csv",
        "base": "legged_gym/logs/original-pipeline-dynamic-terrain/base-v2-16f4736/metrics.csv",
        "color": "#666666",
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
        best_value(spec["base"], "num_waypoints_mean"),
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
