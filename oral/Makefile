PDFLATEX_FLAGS=-synctex=1 -interaction=nonstopmode -file-line-error
PYTHON=conda run -n daily python

FIGURES=figures/curriculum_tiles_labeled.png figures/static_dynamic_waypoints.pdf figures/distillation_waypoints.pdf figures/imitation_losses.pdf figures/recovery_modes_per_family.pdf figures/env_latent_distillation_hurdle.pdf figures/env_latent_distillation_gap.pdf figures/env_latent_distillation_tilted_pads.pdf figures/env_latent_distillation_step.pdf figures/recovery_mode_training_curves.pdf

all: main.pdf

main.pdf: main.tex $(FIGURES)
	pdflatex $(PDFLATEX_FLAGS) main.tex
	pdflatex $(PDFLATEX_FLAGS) main.tex

figures/static_dynamic_waypoints.pdf: figures/plot_static_dynamic_waypoints.py figures/plot_utils.py
	$(PYTHON) figures/plot_static_dynamic_waypoints.py

figures/distillation_waypoints.pdf: figures/plot_distillation_waypoints.py figures/plot_utils.py
	$(PYTHON) figures/plot_distillation_waypoints.py

figures/imitation_losses.pdf: figures/plot_imitation_losses.py figures/plot_utils.py
	$(PYTHON) figures/plot_imitation_losses.py

figures/recovery_modes_per_family.pdf: figures/plot_recovery_modes_per_family.py figures/plot_utils.py
	$(PYTHON) figures/plot_recovery_modes_per_family.py

figures/env_latent_distillation_ablation.pdf: figures/plot_env_latent_distillation_ablation.py figures/plot_utils.py
	$(PYTHON) figures/plot_env_latent_distillation_ablation.py

figures/env_latent_distillation_hurdle.pdf: figures/plot_env_latent_distillation_hurdle.py figures/plot_env_latent_distillation_family.py figures/plot_utils.py
	$(PYTHON) figures/plot_env_latent_distillation_hurdle.py

figures/env_latent_distillation_gap.pdf: figures/plot_env_latent_distillation_gap.py figures/plot_env_latent_distillation_family.py figures/plot_utils.py
	$(PYTHON) figures/plot_env_latent_distillation_gap.py

figures/env_latent_distillation_tilted_pads.pdf: figures/plot_env_latent_distillation_tilted_pads.py figures/plot_env_latent_distillation_family.py figures/plot_utils.py
	$(PYTHON) figures/plot_env_latent_distillation_tilted_pads.py

figures/env_latent_distillation_step.pdf: figures/plot_env_latent_distillation_step.py figures/plot_env_latent_distillation_family.py figures/plot_utils.py
	$(PYTHON) figures/plot_env_latent_distillation_step.py

figures/recovery_mode_training_curves.pdf: figures/plot_recovery_mode_training_curves.py figures/plot_utils.py
	$(PYTHON) figures/plot_recovery_mode_training_curves.py

figures/depth_loss_base_comparison.pdf: figures/plot_depth_loss_base_comparison.py figures/plot_utils.py
	$(PYTHON) figures/plot_depth_loss_base_comparison.py

figures/depth_loss_distill_comparison.pdf: figures/plot_depth_loss_distill_comparison.py figures/plot_utils.py
	$(PYTHON) figures/plot_depth_loss_distill_comparison.py

clean:
	rm -f main.aux main.log main.nav main.out main.snm main.synctex.gz main.toc

.PHONY: all clean
