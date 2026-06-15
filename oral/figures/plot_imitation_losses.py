from pathlib import Path

import matplotlib.pyplot as plt

from plot_utils import apply_style, read_metrics, save_pdf, smooth


OUT = Path(__file__).with_name("imitation_losses.pdf")
CSV = "legged_gym/logs/augment-latent-hybrid-mixed-terrain/imitate-base-15k/imitation_metrics.csv"
WINDOW = 10

METRICS = {
    "action loss": ("action_loss", "#2ca02c"),
    "history action": ("hist_action_loss", "#1f77b4"),
    "estimator": ("estimator_loss", "#9467bd"),
    "dynamic ROA": ("dynamic_env_roa_loss", "#ff7f0e"),
}


apply_style()
df = read_metrics(CSV)
plt.figure(figsize=(7.0, 3.6))
for label, (key, color) in METRICS.items():
    plt.plot(df["checkpoint"], smooth(df[key], WINDOW), lw=2.0, color=color, label=label)

plt.xlabel("imitation iteration")
plt.ylabel("loss")
plt.ylim(0.0, 0.30)
plt.legend(ncol=2, loc="upper right")
save_pdf(OUT)
