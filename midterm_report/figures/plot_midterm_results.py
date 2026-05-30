from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = Path(__file__).resolve().parent

RUNS = [
    (
        "Static base",
        "legged_gym/logs/original-pipeline-static-terrain/base/metrics.csv",
        "#1f77b4",
    ),
    (
        "Dynamic base",
        "legged_gym/logs/original-pipeline-dynamic-terrain/base-v2-16f4736/metrics.csv",
        "#d62728",
    ),
    (
        "Dynamic distill",
        "legged_gym/logs/original-pipeline-dynamic-terrain/distill-from-15k-v2-16f4736/metrics.csv",
        "#9467bd",
    ),
    (
        "DAgger + dynamic base",
        "legged_gym/logs/imitation-pretrain-dynamic-terrain/resume-from-base-15k/metrics.csv",
        "#2ca02c",
    ),
]


def load_metrics(relative_path: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / relative_path).sort_values("checkpoint")
    return df.reset_index(drop=True)


def plot_training_curves() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.55), sharex=False)
    metrics = [
        ("num_waypoints_mean", "Mean waypoints reached"),
        ("reward_mean", "Mean episode reward"),
    ]

    for ax, (metric, ylabel) in zip(axes, metrics):
        for label, path, color in RUNS:
            df = load_metrics(path)
            smooth = df[metric].rolling(5, center=True, min_periods=1).mean()
            ax.plot(
                df["checkpoint"] / 1000.0,
                smooth,
                label=label,
                color=color,
                linewidth=1.8,
            )
        ax.set_xlabel("RL iteration (k)")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.28, linewidth=0.6)

    axes[0].legend(
        loc="upper center",
        bbox_to_anchor=(1.05, 1.32),
        ncol=2,
        frameon=False,
        fontsize=8,
    )
    fig.tight_layout(pad=0.4)
    fig.savefig(FIG_DIR / "training_curves.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_pipeline_diagram() -> None:
    image_path = FIG_DIR / "pipeline_background.png"
    image = mpimg.imread(image_path)

    fig, ax = plt.subplots(figsize=(7.1, 3.1))
    ax.imshow(image)
    ax.axis("off")

    labels = [
        ("Static expert\npolicy", 0.125, 0.90, "#1f5f99"),
        ("Dynamic-obstacle\nIsaac Gym task", 0.375, 0.90, "#4e8d45"),
        ("DAgger imitation\npretraining", 0.625, 0.90, "#b47a00"),
        ("RL fine-tuning\nand distillation", 0.875, 0.90, "#d6651f"),
    ]
    for text, x, y, color in labels:
        ax.text(
            x,
            y,
            text,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=color,
            bbox={
                "boxstyle": "round,pad=0.24",
                "facecolor": "white",
                "edgecolor": color,
                "linewidth": 0.9,
                "alpha": 0.94,
            },
        )

    fig.tight_layout(pad=0)
    fig.savefig(FIG_DIR / "pipeline_diagram.pdf", bbox_inches="tight")
    plt.close(fig)


def add_box(ax, xy, width, height, text, facecolor, edgecolor):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.025,rounding_size=0.03",
        linewidth=1.1,
        facecolor=facecolor,
        edgecolor=edgecolor,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=8.2,
        color="#202020",
        linespacing=1.12,
    )


def add_arrow(ax, start, end, color="#555555", connectionstyle="arc3"):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.1,
        color=color,
        connectionstyle=connectionstyle,
    )
    ax.add_patch(arrow)


def plot_goal_pipeline_diagram() -> None:
    fig, ax = plt.subplots(figsize=(7.1, 3.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.95,
        "Goal: dynamic-state-aware distillation pipeline",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#1d2b38",
    )

    add_box(
        ax,
        (0.03, 0.56),
        0.20,
        0.25,
        "Dynamic parkour\nsimulation\n\nscripted obstacles\nprivileged state",
        "#eef6ff",
        "#2d6ca2",
    )
    add_box(
        ax,
        (0.29, 0.56),
        0.20,
        0.25,
        "Augmented latent\nstate z\n\nhurdle position\ngap configuration\nstep height\nramp / pad angle",
        "#f1fbef",
        "#4e8d45",
    )
    add_box(
        ax,
        (0.55, 0.56),
        0.20,
        0.25,
        "Depth-based\nstudent policy\n\nrecover z explicitly\nor implicitly from\nobservations",
        "#fff7e8",
        "#c98500",
    )
    add_box(
        ax,
        (0.79, 0.56),
        0.18,
        0.25,
        "Select final\nextension\n\nperformance\n+\ntraining stability",
        "#fff0ed",
        "#d6651f",
    )

    add_box(
        ax,
        (0.26, 0.16),
        0.15,
        0.20,
        "ROA-style\nlatent\nestimation",
        "#f8fbff",
        "#6d8fbc",
    )
    add_box(
        ax,
        (0.43, 0.16),
        0.15,
        0.20,
        "Teacher-\nstudent\ndistillation",
        "#f8fbff",
        "#6d8fbc",
    )
    add_box(
        ax,
        (0.60, 0.16),
        0.15,
        0.20,
        "Hybrid\nlatent +\ndistillation",
        "#f8fbff",
        "#6d8fbc",
    )

    add_arrow(ax, (0.23, 0.685), (0.29, 0.685))
    add_arrow(ax, (0.49, 0.685), (0.55, 0.685))
    add_arrow(ax, (0.75, 0.685), (0.79, 0.685))
    add_arrow(ax, (0.39, 0.56), (0.335, 0.36), connectionstyle="arc3,rad=0.15")
    add_arrow(ax, (0.43, 0.56), (0.505, 0.36), connectionstyle="arc3,rad=0.0")
    add_arrow(ax, (0.47, 0.56), (0.675, 0.36), connectionstyle="arc3,rad=-0.15")
    add_arrow(ax, (0.41, 0.26), (0.79, 0.60), connectionstyle="arc3,rad=-0.25")
    add_arrow(ax, (0.58, 0.26), (0.80, 0.59), connectionstyle="arc3,rad=-0.12")
    add_arrow(ax, (0.75, 0.26), (0.83, 0.56), connectionstyle="arc3,rad=0.08")

    ax.text(
        0.50,
        0.44,
        "candidate Phase-2/distillation mechanisms",
        ha="center",
        va="center",
        fontsize=8,
        color="#4b5563",
    )

    fig.tight_layout(pad=0.2)
    fig.savefig(FIG_DIR / "goal_pipeline_diagram.pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    plot_training_curves()
    plot_pipeline_diagram()
    plot_goal_pipeline_diagram()


if __name__ == "__main__":
    main()
