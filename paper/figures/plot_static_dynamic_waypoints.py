from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import apply_style, keep_until, read_metrics, save_pdf, smooth


OUT = Path(__file__).with_name("static_dynamic_waypoints.pdf")
WINDOW = 5
MAX_CHECKPOINT = 50000

RUNS = {
    "original static": {
        "path": "legged_gym/logs/original-pipeline-static-terrain/base/metrics.csv",
        "color": "#1f77b4",
    },
    "original dynamic": {
        "path": "legged_gym/logs/original-pipeline-dynamic-terrain/base-v2-16f4736/metrics.csv",
        "color": "#666666",
    },
}


apply_style()
plt.figure(figsize=(7.0, 3.6))
for label, spec in RUNS.items():
    df = keep_until(read_metrics(spec["path"]), MAX_CHECKPOINT)
    plt.plot(
        df["checkpoint"],
        smooth(df["num_waypoints_mean"], WINDOW),
        lw=2.2,
        color=spec["color"],
        label=label,
    )

plt.xlabel("training iteration")
plt.ylabel("mean waypoints")
plt.ylim(0.0, 1.05)
plt.legend(ncol=2, loc="lower right")
save_pdf(OUT)
