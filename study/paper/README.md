# Overleaf instructions

1. Create a new Overleaf project and upload the whole `paper/` folder
   (`main.tex`, `refs.bib`, `figs/`). Or: **New Project -> Upload Project**
   with a zip of this folder.
2. Set **Compiler: pdfLaTeX** and **Main document: main.tex**
   (Menu -> Settings).
3. Compile. No image files are needed -- every figure is native `pgfplots`
   generated from the result JSONs by `../mkpgf.py`, so the plots are
   editable LaTeX rather than bitmaps.

## Layout switch

`main.tex` opens in double-spaced single-column review layout:

    \documentclass[journal,onecolumn,12pt,draftclsnofoot]{IEEEtran}

For the final two-column submission layout, comment that line and uncomment

    \documentclass[journal]{IEEEtran}

## Before you submit

`refs.bib` contains two verified entries and a block of TODO items. The
manuscript's Related Work deliberately refers to those bodies of work without
citation keys so that no unverified reference enters the bibliography. Complete
items 1--5 in `refs.bib` from publisher records, then add the citations into
Section II.

Also fill in the author block and the funding/acknowledgement footnote in
`main.tex`.

## Regenerating the figures

From the `study/` directory:

    python3 mkpgf.py

which rewrites `paper/figs/*.tex` from `mech_rows.json`, `crit_rows.json`,
`crit_fig2.json`, `agg_rows.json`, `hold_rows.json` and `i69_rows.json`.
