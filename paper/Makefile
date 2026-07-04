PDFLATEX_FLAGS=-synctex=1 -interaction=nonstopmode -file-line-error
PYTHON=conda run -n daily python

FIGURES=\
	figures/static_dynamic_waypoints.pdf \
	figures/distillation_waypoints.pdf \
	figures/imitation_losses.pdf \
	figures/recovery_modes_per_family.pdf \
	figures/env_latent_distillation_hurdle.pdf \
	figures/env_latent_distillation_gap.pdf \
	figures/env_latent_distillation_tilted_pads.pdf \
	figures/env_latent_distillation_step.pdf \
	figures/recovery_mode_training_curves.pdf \
	figures/depth_loss_distill_comparison.pdf \
	figures/curriculum_tiles_labeled.png \
	figures/training_pipeline_ai.png

all: paper_template.pdf

paper_template.pdf: paper_template.tex references.bib $(FIGURES)
	pdflatex $(PDFLATEX_FLAGS) paper_template.tex
	bibtex paper_template
	pdflatex $(PDFLATEX_FLAGS) paper_template.tex
	pdflatex $(PDFLATEX_FLAGS) paper_template.tex

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
	rm -f paper_template.aux paper_template.bbl paper_template.blg paper_template.log paper_template.out paper_template.synctex.gz

.PHONY: all clean
