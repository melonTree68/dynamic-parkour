from ast import literal_eval
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def read_metrics(relative_path):
    return pd.read_csv(ROOT / relative_path).sort_values("checkpoint")


def aggregate_by_checkpoint(df):
    if "eval_terrain" not in df.columns:
        return df.sort_values("checkpoint")
    return (
        df.groupby("checkpoint", as_index=False)[
            ["reward_mean", "num_waypoints_mean", "edge_violation_mean"]
        ]
        .mean()
        .sort_values("checkpoint")
    )


def best_waypoint_before(relative_path, max_checkpoint=None):
    df = aggregate_by_checkpoint(read_metrics(relative_path))
    if max_checkpoint is not None:
        df = df[df["checkpoint"] <= max_checkpoint]
    row = df.loc[df["num_waypoints_mean"].idxmax()]
    return float(row["num_waypoints_mean"])


def smooth(series, window):
    return series.rolling(window, center=True, min_periods=1).mean()


def best_value(relative_path, key):
    return float(pd.read_csv(ROOT / relative_path)[key].max())


def terrain_family(value):
    parsed = literal_eval(value)
    return parsed[0] if len(parsed) == 1 else ""


def apply_style():
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_pdf(path):
    for ax in plt.gcf().axes:
        ax.grid(True, axis="y", alpha=0.25)
        ax.grid(False, axis="x")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
