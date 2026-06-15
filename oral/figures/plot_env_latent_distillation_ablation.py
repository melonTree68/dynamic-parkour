from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import (
    aggregate_by_checkpoint,
    apply_style,
    best_waypoint_before,
    read_metrics,
    save_pdf,
    smooth,
)


OUT = Path(__file__).with_name("env_latent_distillation_ablation.pdf")
WINDOW = 5

RUNS = {
    "no aug": {
        "distill": "legged_gym/logs/imitation-pretrain-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-15k-v2-91bf8ce/metrics.csv",
        "base": "legged_gym/logs/imitation-pretrain-dynamic-terrain/resume-from-imitate-base-15k-100-v2-91bf8ce/metrics.csv",
        "color": "#2ca02c",
    },
    "pure ROA": {
        "distill": "legged_gym/logs/augment-latent-roa-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-20k/metrics.csv",
        "base": "legged_gym/logs/augment-latent-roa-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#ff7f0e",
    },
    "pure teacher-student": {
        "distill": "legged_gym/logs/augment-latent-ts-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-20k/metrics.csv",
        "base": "legged_gym/logs/augment-latent-ts-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "color": "#9467bd",
    },
}


apply_style()
plt.figure(figsize=(7.0, 3.6))
for label, spec in RUNS.items():
    df = aggregate_by_checkpoint(read_metrics(spec["distill"]))
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
plt.ylim(0.0, 0.75)
plt.legend(loc="lower right")
save_pdf(OUT)
