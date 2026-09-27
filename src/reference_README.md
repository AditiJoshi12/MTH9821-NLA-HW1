# Learning an American Put Exercise Boundary

Read `assignment.pdf` for the model, tasks, parameters, and assessment.
`assignment.tex`, `references.bib`, and `exercise_boundary.png` are its source files.
The two reference files supply the numerical benchmark used in the project.
The report has a five-page limit followed by references. Part 1 includes the
dividend-ordering proof, the call exercise-timing explanation, and diagnostics
computed from the existing reference and fitted boundary arrays.

## Reference verification

Use Python 3.12 or later with NumPy and SciPy. From this directory run:

```bash
python reference_solver.py --verify
```

The command checks the saved arrays and repeats spatial and time-integration
refinements for all four cases. It prints a JSON record for each case. Preserve
the supplied `reference_results.npz`; `--verify` reads it and reports comparisons.
The recorded computation used Python 3.12.14, NumPy 2.5.3, and SciPy 1.18.1.

The reference uses a stock grid from 0 to 400 with spacing 0.05, and 32 pricing
substeps per exercise interval. Exercise is applied only at the specified
exercise dates. Refinement records compare stock spacings 0.10 and 0.05 with
16 substeps, then 16 and 32 substeps at spacing 0.05. Report the maximum absolute
price change at the three specified starting spots and the maximum absolute
boundary change across exercise dates. These changes are empirical measures
of numerical stability.

## Reference array names

Load with `numpy.load("reference_results.npz", allow_pickle=False)`.
The four case prefixes are `N180_d0`, `N180_d0125`, `N360_d0`, `N360_d0125`.
For a prefix `key`, the arrays are:

| Array | Meaning |
| --- | --- |
| `spots` | Stock-coordinate grid shared by all cases |
| `key + "_value0"` | Time-zero reference value at each entry of `spots` |
| `key + "_times"` | Calendar times from 0 to T, inclusive |
| `key + "_boundary"` | Boundary at each time, in stock-price units |
| `key + "_dividend_indices"` | The three integer dividend indices |
| `metadata_json` | JSON text containing parameters and numerical diagnostics |

Read a price using `numpy.interp(S0, archive["spots"], archive[key + "_value0"])`.
Boundary arrays have length N+1 and include the terminal convention b(T)=K.
At dividend indices the boundary refers to the state after the dividend.

## Random-draw and arithmetic conventions

Follow these conventions with the seeds in the assignment. Each sample bank
uses its own NumPy `default_rng(seed)`. Let M be its path count.

1. To sample M starting prices, first draw `v = rng.random(M)`, then
   `u = rng.random(M)`. If `v[i] < 0.5`, set
   `A[i] = K * exp(log(0.001) * (1-u[i]))`; otherwise set
   `A[i] = K * (0.2+u[i])`.
2. For regression paths, draw the starting prices, then the normal array with
   `rng.standard_normal((M,N), dtype=numpy.float64)`.
3. For a random-start neural bank, first draw
   `J = rng.integers(0,N,size=M,dtype=numpy.int64)`, then the starting prices,
   then the full normal array of shape `(M,N)` in the same row-major order.
   Column j supplies the increment whose target date is j+1. Set its log
   increment to zero for a path if `j+1 <= J[i]`. Store A in every slot through J.
4. For each path, form log increments with the Gaussian drift and volatility
   terms. Add `log1p(-delta)` in columns immediately preceding dividend indices.
   Accumulate with `numpy.cumsum` across columns, exponentiate, and multiply by
   the starting price. Apply the random-start mask before the cumulative sum.
5. For each final starting spot, use an advancing generator to draw ten
   consecutive normal arrays of shape `(5000,N)`. Reuse each simulated batch
   for every policy evaluated at that spot. For the perturbation experiment,
   reuse the case-3, S0=100 batches.

Construct neural networks in chronological interval order. Within each network,
construct `Linear(1,8)`, then `Tanh()`, then `Linear(8,1)`. Initialize in float32.
The prescribed PyTorch seed is set once before this construction. Use
`torch.randint(8192, (512,))` for each payoff minibatch, retaining the generator
state after initialization. Use two CPU computation threads, one inter-operation
thread, and deterministic algorithms for reproducing the supplied instructor
run. Record your own environment as requested in the handout.

Floating-point libraries and hardware can change numerical results slightly.
The report should interpret the results actually produced by its documented run.

## Reading links

- [Cox and Rubinstein, Options Markets](https://www.afajof.org/wp-content/uploads/files/historical-texts/cox-rubinstein-ocr-1985.pdf)
- [Longstaff and Schwartz, Valuing American Options by Simulation](https://people.math.ethz.ch/~hjfurrer/teaching/LongstaffSchwartzAmericanOptionsLeastSquareMonteCarlo.pdf)
- [Becker, Cheridito, and Jentzen, Deep Optimal Stopping](https://www.jmlr.org/papers/volume20/18-232/18-232.pdf)
- [Buehler, Gonon, Teichmann, and Wood, Deep Hedging](https://arxiv.org/pdf/1802.03042)

The handout specifies which topics to read for the project.

## Building the handout

With a LaTeX installation containing biblatex and its BibTeX backend:

```bash
pdflatex -interaction=nonstopmode -halt-on-error assignment.tex
bibtex assignment
pdflatex -interaction=nonstopmode -halt-on-error assignment.tex
pdflatex -interaction=nonstopmode -halt-on-error assignment.tex
```
