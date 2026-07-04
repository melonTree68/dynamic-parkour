from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import (
    apply_style,
    best_waypoint_before,
    keep_until,
    read_metrics,
    save_pdf,
    smooth,
    terrain_family,
)


WINDOW = 5
MAX_CHECKPOINT = 15000
BASE_MAX_CHECKPOINT = 20000

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


def family_df(relative_path, family, max_checkpoint):
    df = keep_until(read_metrics(relative_path), max_checkpoint)
    df = df.assign(family=df["eval_terrain"].apply(terrain_family))
    df = df[df["family"].str.contains(family)]
    return df.groupby("checkpoint", as_index=False)["num_waypoints_mean"].mean()


def best_family_waypoint(relative_path, family):
    df = family_df(relative_path, family, BASE_MAX_CHECKPOINT)
    if df.empty:
        return None
    return float(df["num_waypoints_mean"].max())


def plot_family(family, label, out_path):
    apply_style()
    plt.figure(figsize=(7.0, 3.6))
    for run_label, spec in RUNS.items():
        df = family_df(spec["distill"], family, MAX_CHECKPOINT)
        color = spec["color"]
        plt.plot(
            df["checkpoint"],
            smooth(df["num_waypoints_mean"], WINDOW),
            lw=2.2,
            color=color,
            label=run_label,
        )
        base_value = best_family_waypoint(spec["base"], family)
        if base_value is None:
            base_value = best_waypoint_before(spec["base"], BASE_MAX_CHECKPOINT)
        plt.axhline(
            base_value,
            color=color,
            lw=1.4,
            ls="--",
            alpha=0.75,
        )

    plt.title(label)
    plt.xlabel("distillation iteration")
    plt.ylabel("mean waypoints")
    plt.ylim(0.0, 1.05)
    plt.legend(loc="lower right")
    save_pdf(Path(out_path))
