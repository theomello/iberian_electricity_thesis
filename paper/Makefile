# Build the thesis and the submission copy.
#   make             -> build/main.pdf
#   make count       -> character count of the main text (limit 60,000-120,000)
#   make submission MATRIKEL=12345678 NAME=First-Last
#                    -> <MATRIKEL>_<NAME>_Masterarbeit_Abgabeversion_<DD-MM-YYYY>.pdf (ISC naming;
#                       no umlauts or special characters), plan boxes hidden, warns above 11 MB.
PY := ../.venv/bin/python
DATE ?= $(shell date +%d-%m-%Y)

.PHONY: pdf count submission clean
pdf:
	latexmk main.tex

count:
	$(PY) ../scripts/qa/paper_charcount.py

submission:
	@test -n "$(MATRIKEL)" -a -n "$(NAME)" || (echo "set MATRIKEL=... NAME=First-Last"; exit 1)
	@echo "$(MATRIKEL)_$(NAME)" | grep -Eq '^[A-Za-z0-9_-]+$$' || (echo "only A-Z, a-z, 0-9, - and _ allowed"; exit 1)
	latexmk -jobname=submission -usepretex='\AtBeginDocument{\showplansfalse}' main.tex
	cp build/submission.pdf "$(MATRIKEL)_$(NAME)_Masterarbeit_Abgabeversion_$(DATE).pdf"
	@$(PY) -c "import os,sys; f=sys.argv[1]; s=os.path.getsize(f)/1e6; print(f'{f}: {s:.1f} MB' + ('  WARNING: over 11 MB, contact the ISC before the deadline' if s>11 else ''))" "$(MATRIKEL)_$(NAME)_Masterarbeit_Abgabeversion_$(DATE).pdf"

clean:
	latexmk -C main.tex
