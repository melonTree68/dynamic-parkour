TEX = paper_template
LATEX = pdflatex -synctex=1 -interaction=nonstopmode -file-line-error
MPLCONFIGDIR = /private/tmp/extreme-parkour-mplconfig
XDG_CACHE_HOME = /private/tmp/extreme-parkour-xdg-cache

.PHONY: all figures clean

all: figures $(TEX).pdf

figures:
	mkdir -p $(MPLCONFIGDIR) $(XDG_CACHE_HOME)
	MPLCONFIGDIR=$(MPLCONFIGDIR) XDG_CACHE_HOME=$(XDG_CACHE_HOME) conda run -n datasci-py313 python figures/plot_midterm_results.py

$(TEX).pdf: $(TEX).tex references.bib figures/pipeline_diagram.pdf figures/training_curves.pdf
	$(LATEX) $(TEX).tex
	bibtex $(TEX)
	$(LATEX) $(TEX).tex
	$(LATEX) $(TEX).tex

clean:
	rm -f $(TEX).aux $(TEX).bbl $(TEX).blg $(TEX).log $(TEX).out $(TEX).synctex.gz
