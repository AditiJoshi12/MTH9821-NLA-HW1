# MTH 9821 — Learning an American Put Exercise Boundary (Assignment 1)

Baruch MFE, Scientific Computing in Finance, Fall 2026.
Team: Aditi Joshi, Helen Siavelis, Jaskaran Kalra, William McDonnell.

**Deliverables**

* `report.docx` — the report (5 pages + references).
* `slides.pptx` — the presentation.
* `results.csv` — every reported number in long format: prices, 95% interval endpoints, boundary errors, ordering diagnostics, LS diagnostics, perturbation, validation, selected checkpoints, timings, and environment.

## Reproduce everything

```bash
pip install -r requirements.txt
python run_all.py            # ~3 min on 2 CPU threads; rebuilds tables/, figures/, fitted/, results.csv, report, slides
python run_all.py --no-docs  # skip report/slides (they need pandoc, python-docx, node + pptxgenjs)
```

`run_all.py` runs the steps in the order the assignment requires. All fitting and checkpoint selection finish before any final evaluation path is generated.

| Step | Script | Part |
|---|---|---|
| 1 | `validate_solver.py` | Checks of our grid solver: European closed form, grid refinement |
| 2 | `run_part1.py` | Part 1 experiments (dividend identity, cap, ordering, call timing) |
| 3 | `run_parts23.py` | Part 2 reference study and simulation; Part 3 Longstaff–Schwartz |
| 4 | `run_part4.py` | Part 4 PyTorch boundary: supervised init, payoff optimisation, validation |
| 5 | `run_part5.py` | Part 5 independent evaluation, boundary accuracy, perturbation |
| 6 | `build_report_final.py`, `deck_data.py`, `build_deck.js` | Report and slides, built from `tables/` |

## Code map

| Module | Role |
|---|---|
| `config.py` | Parameters, time grid with integer dividend indices, cap $U_j$ |
| `lognormal_kernel.py`, `grid_solver.py`, `analytics.py` | Our grid-exercise reference solver and its closed-form checks |
| `reference.py` | Single entry point for "the reference" (see Assumptions) |
| `simulation.py` | Exact path simulation, training distribution $A$, seeded path sets |
| `lsm.py` | LS regression → threshold → cap, replay check, hard exercise rule |
| `nn_policy.py` | Boundary networks, randomised-stopping objective, training and selection |
| `evaluate.py`, `part5.py` | Prices, paired differences, boundary errors, ordering diagnostics, perturbation |
| `experiments_part1.py`, `part2_reference_check.py` | Part 1 experiments; Part 2 refinement study |
| `plotting.py`, `plotting_p23.py` | Figures ($u=T-t$ horizontal, $b/K$ vertical) |

Walkthrough notebooks: `part1_walkthrough.ipynb`, `part23_walkthrough.ipynb`, `part4_walkthrough.ipynb`, `part5_walkthrough.ipynb`.

Saved fits are in `fitted/`:

* LS thresholds and every NN checkpoint boundary (`.npz`);
* NN parameters (`.pt`);
* run configurations with seeds, versions, hardware and timings (`.json`).

## Assumptions (also stated in the report)

* **Reference.** The assignment refers to a supplied `reference_solver.py`, `reference_results.npz` and `README.md`. We did not receive them. The numerical reference is our own grid-exercise solver, which matches European closed forms to about 2e-5 and changes by about 1e-5 under grid refinement. To use the supplied arrays, fill in `SUPPLIED_KEYS` in `reference.py` and rerun.
* **Random-draw order.** The seeds follow the assignment. The order of draws within each seed is our own documented choice, set out in the docstrings of `simulation.py` and `nn_policy.py`.
* **Precision.** float64 for simulation and evaluation; float32 for neural training.

## Environment

Python 3.11, NumPy 2.4, SciPy 1.17, pandas 3.0, PyTorch 2.14 (CPU), 2 CPU threads, no accelerator. See `requirements.txt` and `fitted/run_config*.json`.
