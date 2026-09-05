# Overleaf: how to compile

1. **New Project → Upload Project** with `paper_overleaf.zip` (or upload this
   folder's contents).
2. Menu → **Compiler: pdfLaTeX**, **Main document: main.tex**.
3. Compile twice (BibTeX run in between happens automatically on Overleaf).

Files:

    main.tex        the manuscript (IEEEtran, lettersize/journal)
    refs.bib        13 verified references; see the header note in that file
    IEEEtran.cls    the class file from the supplied template
    fig1.png        placeholder author photo used by \IEEEbiography
    figs/*.tex      seven native TikZ/pgfplots figures, no bitmaps

## Before submitting

* Fill in the author block, the `\thanks` footnotes, `\markboth`, and the
  Acknowledgment.
* Replace `fig1.png` with a real author photo, or switch the first
  `\IEEEbiography` to `\IEEEbiographynophoto`.
* `main.tex` contains one `%TODO: verify citation` comment in Section II. Cite
  two or three electric-bus charging-coordination papers there once their
  records are verified, or leave the claim uncited.
* Spot-check `refs.bib` issue numbers and months on IEEE Xplore.

## Regenerating the data figures

From the parent `study/` directory:

    python3 mkpgf.py

rewrites `figs/fig_boundary.tex`, `fig_closedloop.tex`, `fig_collapse.tex` and
`fig_split.tex` from the result JSONs. The three schematic figures
(`fig_topology.tex`, `fig_timing.tex`, `fig_arch.tex`) are hand-drawn TikZ and
are not regenerated.
