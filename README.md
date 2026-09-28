# MTH 9821 — Learning an American Put Exercise Boundary (Assignment 1)

Baruch MFE, Scientific Computing in Finance, Fall 2026.
Team: Aditi Joshi, Helen Siavelis, Jaskaran Kalra, William McDonnell.

**Deliverables (this folder)**

* [`report.docx`](report.docx) — the report (5 pages + references).
* [`slides.pptx`](slides.pptx) — the presentation.

Everything else is in [`src/`](src):

* code and notebooks;
* `src/results.csv` — every reported number in long format: prices, 95% interval endpoints, boundary errors, ordering diagnostics, LS diagnostics, perturbation, validation, selected checkpoints, timings, and environment;
* tables in `src/tables/`, figures in `src/figures/`, and saved fits in `src/fitted/`.

## Reproduce everything

```bash
pip install -r requirements.txt
cd src
python run_all.py            # ~3 min on 2 CPU threads; rebuilds src/tables, figures, fitted, results.csv, and ../report.docx, ../slides.pptx
python run_all.py --no-docs  # skip report/slides (they need pandoc, python-docx, node + pptxgenjs)
```

`run_all.py` runs the steps in the order the assignment requires. All fitting and checkpoint selection finish before any final evaluation path is generated.

| Step | Script | Part |
|---|---|---|
| 1 | `validate_solver.py` | Checks of our cross-check solver: European closed form, grid refinement |
| 2 | `run_part1.py` | Part 1 experiments (dividend identity, cap, ordering, call timing) |
| 3 | `run_parts23.py` | Part 2 supplied `--verify`, cross-check and simulation; Part 3 Longstaff–Schwartz |
| 4 | `run_part4.py` | Part 4 PyTorch boundary: supervised init, payoff optimisation, validation |
| 5 | `run_part5.py` | Part 5 independent evaluation, boundary accuracy, perturbation |
| 6 | `build_report_final.py`, `deck_data.py`, `build_deck.js` | Report and slides, built from `tables/` |

## Code map (all in `src/`)

| Module | Role |
|---|---|
| `config.py` | Parameters, time grid with integer dividend indices, cap $U_j$ |
| `reference_solver.py`, `reference_results.npz` | Supplied instructor reference (unchanged) |
| `lognormal_kernel.py`, `grid_solver.py`, `analytics.py` | Our independent grid solver (Part 1 illustrations, cross-check) and its closed-form checks |
| `reference.py`, `part2_supplied_verify.py` | Supplied reference arrays and their `--verify` run; cross-check against our solver |
| `simulation.py` | Exact path simulation, training distribution $A$, seeded path sets |
| `lsm.py` | LS regression → threshold → cap, replay check, hard exercise rule |
| `nn_policy.py` | Boundary networks, randomised-stopping objective, training and selection |
| `evaluate.py`, `part5.py` | Prices, paired differences, boundary errors, ordering diagnostics, perturbation |
| `experiments_part1.py`, `part2_reference_check.py` | Part 1 experiments; Part 2 refinement study |
| `plotting.py`, `plotting_p23.py` | Figures ($u=T-t$ horizontal, $b/K$ vertical) |

Walkthrough notebooks: `part1_walkthrough.ipynb`, `part23_walkthrough.ipynb`, `part4_walkthrough.ipynb`, `part5_walkthrough.ipynb`.

Saved fits are in `src/fitted/`:

* LS thresholds and every NN checkpoint boundary (`.npz`);
* NN parameters (`.pt`);
* run configurations with seeds, versions, hardware and timings (`.json`).

## Reference and conventions

* **Supplied reference (unchanged).** The instructor files are kept unchanged in `src/`:
  * `reference_solver.py`
  * `reference_results.npz`
  * `reference_README.md` — the supplied `README.md`, renamed so it doesn't clash with this one.

  `reference.py` reads the saved arrays. `part2_supplied_verify.py` runs `python reference_solver.py --verify`, which passed. Our own grid solver (`grid_solver.py`) is used only for the Part 1 illustrations and as an independent cross-check; it agrees with the supplied arrays to about 1e-5 in price.
* **Random draws.** All samples follow the supplied README's draw order and arithmetic, and the seeds from the assignment.
* **PyTorch settings.** 2 threads, 1 inter-op thread, deterministic algorithms.
* **Precision.** float64 for simulation and evaluation; float32 for neural training.

## Environment

Python 3.11, NumPy 2.4, SciPy 1.17, pandas 3.0, PyTorch 2.14 (CPU), 2 CPU threads, no accelerator. See `requirements.txt` and `src/fitted/run_config*.json`.
