"""
run_all.py -- One command that reproduces every result, figure, the report
(../report.docx) and the slides (../slides.pptx),
which are written to the repository root, in the order the assignment requires (all fitting and
checkpoint selection finish before any final evaluation path is drawn).

    cd src
    python run_all.py            # ~3-4 minutes on 2 CPU threads
    python run_all.py --no-docs  # skip report/slides (no pandoc / node needed)
"""
import subprocess
import sys

STEPS = [
    ["python", "validate_solver.py"],     # solver checks (Part 2 reference placeholder)
    ["python", "run_part1.py"],           # Part 1 experiments
    ["python", "run_parts23.py"],         # Parts 2-3: reference study, simulation, LS
    ["python", "run_part4.py"],           # Part 4: neural policy, validation, selection
    ["python", "run_part5.py"],           # Part 5: final evaluation, perturbation, results.csv
]
DOCS = [
    ["python", "build_report_final.py"],  # report.docx (submitted, <= 5 pages)
    ["python", "deck_data.py"],
    ["node", "build_deck.js"],            # slides.pptx
]

if __name__ == "__main__":
    for cmd in STEPS + ([] if "--no-docs" in sys.argv else DOCS):
        print(">>", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    print("done")
