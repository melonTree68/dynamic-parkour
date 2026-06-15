from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import apply_style, best_value, read_metrics, save_pdf, smooth


OUT = Path(__file__).with_name("distillation_waypoints.pdf")
WINDOW = 5

RUNS = {
    "original dynamic distill": {
        "distill": "legged_gym/logs/original-pipeline-dynamic-terrain/distill-from-15k-v2-16f4736/metrics.csv",
        "base": "legged_gym/logs/original-pipeline-dynamic-terrain/base-v2-16f4736/metrics.csv",
        "color": "#666666",
    },
    "imitation dynamic distill": {
        "distill": "legged_gym/logs/imitation-pretrain-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-15k-v2-91bf8ce/metrics_all.csv",
        "base": "legged_gym/logs/imitation-pretrain-dynamic-terrain/resume-from-imitate-base-15k-100-v2-91bf8ce/metrics_all.csv",
        "color": "#2ca02c",
    },
}


apply_style()
plt.figure(figsize=(7.0, 3.6))
for label, spec in RUNS.items():
    df = read_metrics(spec["distill"])
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
plt.ylim(0.0, 0.75)
plt.legend(loc="lower right")
save_pdf(OUT)
