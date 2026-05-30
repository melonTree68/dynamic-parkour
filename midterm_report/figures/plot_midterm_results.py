from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
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


def main() -> None:
    plot_training_curves()
    plot_pipeline_diagram()


if __name__ == "__main__":
    main()
