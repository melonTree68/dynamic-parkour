from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

proj_name = "imitation-pretrain-dynamic-terrain"
exptid = "imitate-base-15k"
label = "imitate-base-15k"

csv_path = f"legged_gym/logs/{proj_name}/{exptid}/imitation_metrics.csv"
output_path = Path(f"plots/{proj_name}/{exptid}/imitation_metrics")
window = 25

df = pd.read_csv(csv_path).sort_values("checkpoint")
output_path.mkdir(parents=True, exist_ok=True)

x = "checkpoint"
loss_metrics = [
    "action_loss",
    "hist_action_loss",
    "estimator_loss",
    "total_loss",
]

for metric in loss_metrics:
    y_smooth = df[metric].rolling(window, center=True, min_periods=1).mean()
    plt.figure()
    plt.plot(df[x], df[metric], lw=0.8, alpha=0.35)
    plt.plot(df[x], y_smooth, lw=1.5)
    plt.xlabel("iteration")
    plt.ylabel(metric)
    plt.title(f"{label} - {metric}")
    plt.tight_layout()
    plt.savefig(output_path / f"{metric}.png", dpi=300)
    plt.close()
