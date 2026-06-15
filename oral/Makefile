PDFLATEX_FLAGS=-synctex=1 -interaction=nonstopmode -file-line-error
PYTHON=conda run -n daily python

FIGURES=figures/static_dynamic_waypoints.pdf figures/distillation_waypoints.pdf figures/imitation_losses.pdf figures/recovery_modes_per_family.pdf

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

clean:
	rm -f main.aux main.log main.nav main.out main.snm main.synctex.gz main.toc

.PHONY: all clean
