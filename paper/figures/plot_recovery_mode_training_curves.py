from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import (
    apply_style,
    keep_until,
    read_metrics,
    smooth,
    terrain_family,
)


OUT = Path(__file__).with_name("recovery_mode_training_curves.pdf")
WINDOW = 5
BASE_MAX_CHECKPOINT = 20000
DISTILL_MAX_CHECKPOINT = 15000

RUNS = {
    "no aug": {
        "base": "legged_gym/logs/imitation-pretrain-dynamic-terrain/resume-from-imitate-base-15k-100-v2-91bf8ce/metrics.csv",
        "distill": "legged_gym/logs/imitation-pretrain-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-15k-v2-91bf8ce/metrics.csv",
        "color": "#2ca02c",
    },
    "pure ROA": {
        "base": "legged_gym/logs/augment-latent-roa-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "distill": "legged_gym/logs/augment-latent-roa-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-20k/metrics.csv",
        "color": "#ff7f0e",
    },
    "pure teacher-student": {
        "base": "legged_gym/logs/augment-latent-ts-dynamic-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "distill": "legged_gym/logs/augment-latent-ts-dynamic-terrain/distill-from-resume-from-imitate-base-15k-100-20k/metrics.csv",
        "color": "#9467bd",
    },
    "hybrid": {
        "base": "legged_gym/logs/augment-latent-hybrid-mixed-terrain/resume-from-imitate-base-15k-100/metrics.csv",
        "distill": "legged_gym/logs/augment-latent-hybrid-mixed-terrain/distill-from-resume-from-imitate-base-15k-100-20k/metrics.csv",
        "color": "#d62728",
    },
}

FAMILIES = [
    ("hurdle", "Hurdle"),
    ("gap", "Gap"),
    ("tilted_pads", "Tilted pads"),
]


def family_df(relative_path, family, max_checkpoint):
    df = keep_until(read_metrics(relative_path), max_checkpoint)
    df = df.assign(family=df["eval_terrain"].apply(terrain_family))
    df = df[df["family"].str.contains(family)]
    return df.groupby("checkpoint", as_index=False)["num_waypoints_mean"].mean()


def draw_row(axes, stage, max_checkpoint):
    for ax, (family, title) in zip(axes, FAMILIES):
        for label, spec in RUNS.items():
            df = family_df(spec[stage], family, max_checkpoint)
            ax.plot(
                df["checkpoint"],
                smooth(df["num_waypoints_mean"], WINDOW),
                lw=1.5,
                color=spec["color"],
                label=label,
            )
            if stage == "distill":
                base = family_df(spec["base"], family, BASE_MAX_CHECKPOINT)
                if not base.empty:
                    ax.axhline(
                        float(base["num_waypoints_mean"].max()),
                        color=spec["color"],
                        lw=1.0,
                        ls="--",
                        alpha=0.55,
                    )
        ax.set_title(title, fontsize=9, pad=2)
        ax.set_xlim(0, max_checkpoint)
        ax.set_ylim(0.0, 1.02)
        ax.tick_params(labelsize=8)


apply_style()
fig, axes = plt.subplots(2, 3, figsize=(7.4, 4.9), sharey=True)
draw_row(axes[0], "base", BASE_MAX_CHECKPOINT)
draw_row(axes[1], "distill", DISTILL_MAX_CHECKPOINT)

axes[0, 0].set_ylabel("base RL\nwaypoints")
axes[1, 0].set_ylabel("distillation\nwaypoints")
for ax in axes[1]:
    ax.set_xlabel("iteration")

handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.52, 0.99))

for ax in fig.axes:
    ax.grid(True, axis="y", alpha=0.25)
    ax.grid(False, axis="x")
fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
fig.savefig(OUT)
plt.close(fig)
