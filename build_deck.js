// build_deck.js -- PowerPoint deck for Assignment 1 (draft: Parts 1-3).
// Numbers come from deck_data.json (python deck_data.py), figures from figures/.
//   python deck_data.py && node build_deck.js
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const D = JSON.parse(fs.readFileSync("deck_data.json", "utf8"));

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";               // 10 x 5.625 in
pres.title = "Learning an American Put Exercise Boundary";

// ---- palette & type -------------------------------------------------------
const NAVY = "1E2761", ICE = "CADCFC", TINT = "EEF2FB", ORANGE = "EB6834",
      BLUE = "2A78D6", INK = "1B1B1B", MUTED = "5A5F6E", WHITE = "FFFFFF";
const HF = "Cambria", BF = "Calibri";
const fmt = (x, d = 4) => Number(x).toFixed(d);
const sci = (x) => (x === 0 ? "0" : Number(x).toExponential(1));

// ---- helpers --------------------------------------------------------------
function title(slide, text, sub) {
  slide.addText(text, { x: 0.5, y: 0.3, w: 9, h: 0.6, fontFace: HF, fontSize: 28,
    bold: true, color: NAVY, margin: 0, isTextBox: true });
  if (sub) slide.addText(sub, { x: 0.5, y: 0.88, w: 9, h: 0.35, fontFace: BF,
    fontSize: 13, color: MUTED, italic: true, margin: 0, isTextBox: true });
}
function badge(slide, n, x, y, fill = NAVY) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color: fill } });
  slide.addText(String(n), { x, y, w: 0.42, h: 0.42, align: "center", valign: "middle",
    fontFace: HF, fontSize: 14, bold: true, color: WHITE, margin: 0, isTextBox: true });
}
function card(slide, x, y, w, h, fill = TINT) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08,
    fill: { color: fill }, line: { color: fill } });
}
function bullets(slide, items, x, y, w, h, size = 14) {
  slide.addText(items.map((t, i) => ({ text: t, options: { bullet: true,
    breakLine: i < items.length - 1 } })), { x, y, w, h, fontFace: BF, fontSize: size,
    color: INK, valign: "top", paraSpaceAfter: 6, margin: 0.05, isTextBox: true });
}
function stat(slide, big, label, x, y, w, color = NAVY, size = 28) {
  card(slide, x, y, w, 1.15);
  slide.addText(big, { x: x + 0.15, y: y + 0.08, w: w - 0.3, h: 0.6, fontFace: HF,
    fontSize: size, bold: true, color, margin: 0, isTextBox: true });
  slide.addText(label, { x: x + 0.15, y: y + 0.66, w: w - 0.3, h: 0.45, fontFace: BF,
    fontSize: 11, color: MUTED, margin: 0, valign: "top", isTextBox: true });
}
function img(slide, path, x, y, w, pxW, pxH) {
  slide.addImage({ path, x, y, w, h: w * pxH / pxW });
}
function footer(slide, text) {
  slide.addText(text, { x: 0.5, y: 5.2, w: 9, h: 0.3, fontFace: BF, fontSize: 9,
    color: MUTED, italic: true, margin: 0, isTextBox: true });
}

// ---- 1. Title -------------------------------------------------------------
let s = pres.addSlide();
s.background = { color: NAVY };
s.addText("Learning an American Put Exercise Boundary", { x: 0.6, y: 1.4, w: 8.8, h: 1.2,
  fontFace: HF, fontSize: 38, bold: true, color: WHITE, margin: 0, isTextBox: true });
s.addText("Numerical reference, Longstaff–Schwartz regression and neural exercise policies",
  { x: 0.6, y: 2.65, w: 8.8, h: 0.5, fontFace: BF, fontSize: 16, color: ICE, margin: 0, isTextBox: true });
s.addText("Aditi Joshi, Helen Siavelis, Jaskaran Kalra, William McDonnell  ·  Baruch MFE, Scientific Computing in Finance",
  { x: 0.6, y: 4.5, w: 8.8, h: 0.4, fontFace: BF, fontSize: 12, color: ICE, margin: 0, isTextBox: true });
s.addNotes("Draft deck. Parts 1-3 are complete; Parts 4-5 are placeholders. The reference is our own grid solver until the supplied reference_solver.py arrives.");

// ---- 2. Question & setup ---------------------------------------------------
s = pres.addSlide();
title(s, "How accurately must a boundary be learned?", "Price an American put with three proportional dividends; compare a reference, LS and a neural policy");
const params = [["K = 100", "strike"], ["T = 3/4", "years to maturity"], ["r = log 1.05", "continuous rate"],
                ["σ = 0.30", "volatility"], ["δ ∈ {0, 1.25%}", "dividend fraction"], ["N ∈ {180, 360}", "exercise intervals"]];
params.forEach(([b, l], i) => {
  const x = 0.5 + (i % 3) * 3.05, y = 1.45 + Math.floor(i / 3) * 1.35;
  stat(s, b, l, x, y, 2.85);
});
s.addText("Dividends at d = 5/24, 11/24, 17/24 (plot markers u = T − t = 13/24, 7/24, 1/24). Jump S → (1−δ)S, then exercise decision.",
  { x: 0.5, y: 4.3, w: 9, h: 0.6, fontFace: BF, fontSize: 13, color: INK, margin: 0, isTextBox: true });
s.addNotes("All numbers use the risk-neutral measure. Calendar time runs right to left on every boundary plot because the horizontal axis is time remaining.");

// ---- 3. Item 1 & 4: order of dividend and exercise --------------------------
s = pres.addSlide();
title(s, "Put: jump first. Call: decide first.", "Part 1, items 1 and 4 — which side of the dividend to exercise on");
img(s, "figures/p1_pre_jump.png", 0.5, 1.35, 5.9, 1440, 528);
bullets(s, [
  "Put: V(d⁻, s) = V(d⁺, (1−δ)s) ≥ (K − s) + δs, so pre-jump exercise is never optimal.",
  "Call: C(d⁻, s) = max{(s−K)⁺, C(d⁺, (1−δ)s)}; the max binds above s* (104.8 before d₃).",
  `Call value at S₀=100: correct ${fmt(D.call[3]["C(0,100)"])}, put-style ordering ${fmt(D.call[1]["C(0,100)"])}, European ${fmt(D.call[0]["C(0,100)"])}.`,
], 6.6, 1.35, 2.95, 3.6, 12);
footer(s, "Our own grid solver, N = 180, δ = 0.0125. The put-style call exercises one grid step early and loses interest K(1 − e^(−rh)).");
s.addNotes("For the put, exercising just after the jump pays delta*s more with no time elapsed. For the call the intrinsic value falls at the jump, so the call must test exercise before applying the dividend.");

// ---- 4. Item 2: the cap ----------------------------------------------------
s = pres.addSlide();
title(s, "Near a dividend, the boundary rides the cap", "Part 1, item 2 — b(d − ε) ≤ K(1 − e^(−rε)) / δ → 0");
img(s, "figures/p1_cap_zoom.png", 0.5, 1.35, 9, 1600, 528);
stat(s, "≈ 3.9 K / yr", "slope rK/δ of the straight segments in Cox–Rubinstein's figure", 0.5, 4.4 - 0.35, 2.9, ORANGE);
stat(s, "1.63 → 0.81", "one-step cap K(1−e^(−rh))/δ, N = 180 → 360: positive, → 0 with h", 3.55, 4.05, 2.9);
stat(s, "0.69, 0.75, 0.89 K", "b just after d₁, d₂, d₃: the upward jump in calendar time", 6.6, 4.05, 2.9, NAVY, 22);
s.addNotes("Waiting until d+ and exercising gives V >= K e^{-r eps} - (1-delta) s. For small s exercise at d+ is nearly certain, so the bound is attained: the boundary lies on the cap for about 0.13 years before each dividend.");

// ---- 5. Item 3: ordering -----------------------------------------------------
s = pres.addSlide();
title(s, "Dividends can only help the put", "Part 1, item 3 — V₀.₀₁₂₅ ≥ V₀ and b₀.₀₁₂₅ ≤ b₀, equal after d₃");
const steps = ["Couple: same Brownian increments, S^δ = S⁰(1−δ)^n ≤ S⁰",
               "Common stopping time τ ⇒ (K − S^δ_τ)⁺ ≥ (K − S⁰_τ)⁺ on every path",
               "Take expectations, then sup over τ ⇒ V_δ ≥ V₀",
               "V_δ = K − s ⇒ V₀ = K − s: exercise regions nested ⇒ b_δ ≤ b₀"];
steps.forEach((t, i) => {
  const y = 1.4 + i * 0.8;
  badge(s, i + 1, 0.5, y);
  s.addText(t, { x: 1.05, y: y - 0.05, w: 4.6, h: 0.55, fontFace: BF, fontSize: 13, color: INK,
    valign: "middle", margin: 0, isTextBox: true });
});
stat(s, "0 %", `paths with Q_δ < Q₀ under one common τ (coupled MC, 20,000 paths)`, 6.0, 1.35, 3.5, BLUE);
stat(s, `${(D.mc[1].frac_paths_Qd_lt_Q0 * 100).toFixed(1)} %`, "paths violating it when each model uses its own stopping rule", 6.0, 2.65, 3.5, ORANGE);
stat(s, "A = B = F = 0", "reference ordering diagnostics, N = 180 and 360", 6.0, 3.95, 3.5);
s.addNotes("The second stat shows why the proof fixes a common stopping time before comparing payoffs. The reference diagnostics are exact zeros; after d3 the two problems are identical.");

// ---- 6. Part 2: reference verification ---------------------------------------
s = pres.addSlide();
title(s, "Refinement vs changing N", "Part 2 — the reference is precise to ~1e-5 $; changing N changes the problem itself");
const hdr = { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: BF, fontSize: 12 };
const cell = (t, b = false) => ({ text: t, options: { fontFace: BF, fontSize: 12, color: INK, bold: b } });
s.addTable([
  [{ text: "Change", options: hdr }, { text: "Max price change ($)", options: hdr }, { text: "Max boundary change ($)", options: hdr }],
  [cell("Spatial dx/2, dx/4"), cell(sci(D.refine.spatial_dv)), cell(sci(D.refine.spatial_db))],
  [cell("Time integration h/2, h/4"), cell(sci(D.refine.time_dv)), cell(sci(D.refine.time_db))],
  [cell("Wider domain / kernel tails"), cell("0"), cell("≤ 3e-12")],
  [cell("N = 180 → 360", true), cell(sci(D.refine.N_dv), true), cell(fmt(D.refine.N_db, 3), true)],
], { x: 0.5, y: 1.45, w: 5.6, colW: [2.2, 1.7, 1.7], rowH: 0.45, border: { type: "solid", pt: 0.5, color: "D5DAE6" }, fill: { color: WHITE } });
card(s, 6.4, 1.45, 3.1, 2.25);
s.addText([
  { text: "Placeholder reference", options: { bold: true, breakLine: true } },
  { text: "Our own solver: exact Gaussian step on a log grid, dividend = exact 10-node shift, dx²/6 variance correction. European check ≈ 2e-5 $. Replace with the supplied -verify output." },
], { x: 6.55, y: 1.55, w: 2.8, h: 2.05, fontFace: BF, fontSize: 11, color: INK, valign: "top", margin: 0, isTextBox: true });
stat(s, "≈ 1e-5 $", "reference price precision (largest refinement change)", 0.5, 3.95, 2.7, BLUE);
stat(s, "≈ 0.3 $", "boundary shift from N = 180 → 360: a different problem", 3.4, 3.95, 2.7, ORANGE);
footer(s, "A claimed accuracy gain smaller than the reference's own precision (~1e-5 $ in price, ~1e-3 $ in boundary) cannot be resolved.");
s.addNotes("Time refinement barely moves anything because the kernel integrates the lognormal step exactly. More exercise dates raise the value by ~1e-3 dollars and move the boundary by ~0.3 dollars, two orders of magnitude above the refinement changes.");

// ---- 7. Part 2: simulation ----------------------------------------------------
s = pres.addSlide();
title(s, "Exact simulation passes the martingale check", "Part 2 — (mean S_T − S₀e^(rT)(1−δ)³) / SE on the final S₀ = 100 sample");
D.martingale.forEach((z, i) => stat(s, (z >= 0 ? "+" : "") + z.toFixed(2),
  `case ${i}: N = ${i < 2 ? 180 : 360}, δ = ${i % 2 ? "0.0125" : "0"}`, 0.5 + i * 2.28, 1.45, 2.1, Math.abs(z) > 1.9 ? ORANGE : NAVY));
bullets(s, [
  "Exact lognormal step, dividend applied on arrival at an integer dividend index; a start at a dividend date is post-jump.",
  "Training mixture A: log-uniform on [0.001K, K] or uniform on [0.2K, 1.2K], each with probability 1/2.",
  "All four z-scores lie inside ±2; case 2 sits at the edge (1.96), which is plausible for one of four draws.",
  "Assumed draw order (README.md not yet available): coin, log-uniform, uniform per path, then the path normals.",
], 0.5, 2.9, 9, 2.2, 13);
s.addNotes("The draw order must be checked against the supplied README before submission; changing it changes every Monte Carlo number but not the method.");

// ---- 8. Part 3: method ---------------------------------------------------------
s = pres.addSlide();
title(s, "Longstaff–Schwartz, turned into a threshold", "Part 3 — 32,768 paths from S₀ ~ A, targets in time-zero dollars");
const ls = [["Regress", "Y on 1, x, x², x³ over ITM rows (SVD least squares)"],
            ["Clip", "c_j ∈ [0, K e^(−r t_{j+1})] ⇒ H₀ > 0"],
            ["Threshold", "largest +/− crossing of H on s = 0.1ℓ"],
            ["Cap & update", "b_j = min(U_j, candidate); exercised paths get e^(−r t_j)(K − S_j)"]];
ls.forEach(([h, t], i) => {
  const x = 0.5 + i * 2.3;
  card(s, x, 1.5, 2.1, 2.0);
  badge(s, i + 1, x + 0.15, 1.65, ORANGE);
  s.addText(h, { x: x + 0.65, y: 1.65, w: 1.4, h: 0.42, fontFace: HF, fontSize: 15, bold: true,
    color: NAVY, valign: "middle", margin: 0, isTextBox: true });
  s.addText(t, { x: x + 0.15, y: 2.2, w: 1.85, h: 1.25, fontFace: BF, fontSize: 12, color: INK,
    valign: "top", margin: 0, isTextBox: true });
});
const dg = D.ls_diag;
s.addTable([
  ["Case", "Fallbacks", "Multi-crossing dates", "Capped dates", "Replay max|Q−Y|"].map(t => ({ text: t, options: hdr })),
  ...dg.map(r => [String(r.case), String(r.fallback_count), `${r.multi_crossing_count} / ${r.N}`,
                  String(r.capped_count), sci(r.replay_max_abs_diff)].map(t => cell(t))),
], { x: 0.5, y: 3.7, w: 9, colW: [1.2, 1.5, 2.3, 1.8, 2.2], rowH: 0.27, fontSize: 11,
     border: { type: "solid", pt: 0.5, color: "D5DAE6" }, fill: { color: WHITE } });
s.addNotes("The clip upper bound is the most any continuation can be worth in time-zero dollars, since the next exercise is at t_{j+1} and pays at most K. Replaying the frozen rule reproduces the backward targets exactly.");

// ---- 9. Part 3: two crossings -----------------------------------------------
s = pres.addSlide();
title(s, "Why the largest crossing is the right one", "A cubic over [0.001K, K] cannot follow the curvature: H dips below zero near s ≈ 3");
img(s, "figures/p23_H_example.png", 0.5, 1.35, 9, 1520, 544);
footer(s, "Case 0, date j = 90. Selecting the largest crossing gives one exercise interval (0, b] and discards the spurious continuation pocket around s ≈ 3–33.");
s.addNotes("Nearly every date has two positive-to-negative crossings. The rule defines a single interval containing all smaller prices, which is the correct economic shape even though the polynomial itself says otherwise.");

// ---- 10. Part 4: neural boundary ------------------------------------------------
s = pres.addSlide();
title(s, "A neural boundary under the cap", "Part 4 — b_θ(t_j) = U_j · sigmoid(f_θ(t_j)); the cap is built in, the network learns the shape");
[["Architecture", "δ = 0: one net on [0, T]. δ > 0: four nets on [0,d₁), [d₁,d₂), [d₂,d₃), [d₃,T]. Each Linear(1,8) → tanh → Linear(8,1), input x = (t−α)/(β−α)."],
 ["Warm start", "1,000 full-grid Adam steps (lr 0.01) onto the LS thresholds → checkpoint 0."],
 ["Payoff stage", "2,400 Adam steps (lr 0.003), batches of 512 from 8,192 random-start paths; ε = 0.01 → 0.002 after 400."],
 ["Selection", "Hard rule on 4,096 validation paths at checkpoints 0, 400, …, 2,400; best mean wins, ties → earliest."]].forEach(([h, t], i) => {
  const y = 1.4 + i * 0.9;
  badge(s, i + 1, 0.5, y, ORANGE);
  s.addText([{ text: h + ". ", options: { bold: true, color: NAVY } }, { text: t, options: { color: INK } }],
    { x: 1.05, y: y - 0.08, w: 4.7, h: 0.8, fontFace: BF, fontSize: 12, valign: "top", margin: 0, isTextBox: true });
});
card(s, 6.0, 1.35, 3.5, 3.6);
s.addText([
  { text: "Randomised stopping", options: { bold: true, color: NAVY, fontFace: HF, fontSize: 15, breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "p_j = 1{S_j<K} · sigmoid((b_θ(t_j) − S_j)/(εK)),  p_N = 1", options: { breakLine: true } },
  { text: "w_j = p_j · Π_{k<j} (1 − p_k)", options: { breakLine: true } },
  { text: "R_θ = Σ_j w_j e^(−r(t_j − t_J)) (K − S_j)⁺", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "w_j is the probability of stopping first at t_j, so R_θ is the path-conditional expected payoff of a randomised rule: smooth in θ, and equal to the hard rule as ε → 0 (checked to ≤ 1e-6 $).", options: { color: MUTED } },
], { x: 6.15, y: 1.5, w: 3.2, h: 3.35, fontFace: BF, fontSize: 11.5, color: INK, valign: "top", margin: 0, isTextBox: true });
s.addNotes("Becker et al. (2019): one network per date, stop/continue relaxed to a logistic probability, trained backward one date at a time to maximise expected reward; lower bound plus dual upper bound. Bühler et al. (2019): semi-recurrent networks for the hedging strategy, trained with Adam on simulated paths to minimise a convex risk measure (e.g. expected shortfall) under transaction costs. We train one threshold jointly over all dates for expected payoff.");

// ---- 11. Part 4: training and validation ------------------------------------------
s = pres.addSlide();
title(s, "Validation cannot tell the checkpoints apart", "Paired validation gains vs checkpoint 0 are all within ~2 SE");
img(s, "figures/p4_validation.png", 0.5, 1.35, 5.6, 1024, 544);
D.nn_summary.forEach((r, i) => {
  const e = D.nn_E[i];
  const y = 1.35 + i * 0.92;
  card(s, 6.35, y, 3.15, 0.8);
  s.addText([
    { text: `Case ${r.case}: ckpt ${r.selected_checkpoint}`, options: { bold: true, color: NAVY, breakLine: true } },
    { text: `E_mean ${fmt(e.ckpt0, 3)} → ${fmt(e.selected, 3)}`, options: { color: e.selected > e.ckpt0 + 0.005 ? ORANGE : (e.selected < e.ckpt0 - 0.005 ? BLUE : MUTED) } },
  ], { x: 6.5, y: y + 0.08, w: 2.9, h: 0.65, fontFace: BF, fontSize: 12, valign: "top", margin: 0, isTextBox: true });
});
footer(s, "Case 2: payoff training more than halved the boundary error. Case 0: the selected checkpoint drifted to b ≈ 0.49K near t₀, which few validation paths visit.");
s.addNotes("Validation uses random start dates, so dates near t0 carry little weight. Case 0's selected checkpoint has a worse boundary than checkpoint 400 and loses 0.87 dollars at S0 = 60 in the fixed-start evaluation.");

// ---- 12. Figure 1 ----------------------------------------------------------------
s = pres.addSlide();
title(s, "Three boundaries (N = 360)", "Figure 1 — reference (blue), LS (orange), selected neural policy (green), N = 180 reference dashed");
img(s, "figures/fig1_boundaries.png", 0.5, 1.3, 9, 1520, 608);
s.addNotes("The NN smooths the LS noise and removes its downward spikes before dividends, but inherits LS's low level unless payoff training moves it (case 2 did, case 3 selected checkpoint 0).");

// ---- 13. Figure 2 ------------------------------------------------------------------
s = pres.addSlide();
title(s, "Around the final dividend", "Figure 2 — case 3, |t − d₃| ≤ 1/24");
img(s, "figures/fig2_final_dividend.png", 0.5, 1.3, 5.6, 992, 608);
bullets(s, [
  "Right of the dotted line = before d₃ in calendar time: the reference sits exactly on the Part 1 bound.",
  "LS and NN stay below the cap there: the premium δs − K(1 − e^(−rε)) is only cents.",
  "Left = after d₃: no dividend remains and the boundary rises to K; both fits are biased low (~0.15K).",
], 6.3, 1.4, 3.2, 3.5, 12);
s.addNotes("The cap supplies the known pre-dividend behaviour; the fitted functions only determine the shape below it.");

// ---- 14. Prices ----------------------------------------------------------------------
s = pres.addSlide();
title(s, "Large boundary error, small price error", "Part 5 prices — 50,000 independent paths per start, common paths across policies, float64");
const pr = D.prices.filter(p => p.S0 !== 60);
s.addTable([
  ["Case", "S₀", "Reference", "LS (SE)", "NN (SE)"].map(t => ({ text: t, options: hdr })),
  ...pr.map(p => [String(p.case), String(p.S0), fmt(p.ref), `${fmt(p.ls, 3)} (${fmt(p.se, 3)})`, `${fmt(p.nn, 3)} (${fmt(p.nnse, 3)})`].map(t => cell(t))),
], { x: 0.5, y: 1.4, w: 5.6, colW: [0.6, 0.6, 1.2, 1.6, 1.6], rowH: 0.36, fontSize: 11,
     border: { type: "solid", pt: 0.5, color: "D5DAE6" }, fill: { color: WHITE } });
const lsE = D.errors.filter(e => e.method === "LS").map(e => e.E_mean);
const nnE = D.errors.filter(e => e.method === "NN").map(e => e.E_mean);
const loss = D.paired.filter(p => p.S0 > 60 && p.pair === "LS - ref-boundary policy").map(p => -p.diff);
stat(s, `${(Math.min(...lsE) * 100).toFixed(0)}–${(Math.max(...lsE) * 100).toFixed(0)} % | ${(Math.min(...nnE) * 100).toFixed(0)}–${(Math.max(...nnE) * 100).toFixed(0)} %`, "mean boundary error E_mean of K: LS | NN", 6.35, 1.4, 3.15, ORANGE, 24);
stat(s, `${fmt(Math.min(...loss), 2)}–${fmt(Math.max(...loss), 2)} $`, "paired LS price loss vs the reference boundary rule (same paths)", 6.35, 2.7, 3.15, BLUE, 24);
s.addText("S₀ = 60 omitted: LS and the reference exercise at once (value 40); the NN loses 0.87 $ (case 0) and 0.03 $ (case 1) there. Smooth pasting makes price error roughly second order in boundary error.",
  { x: 6.35, y: 4.0, w: 3.15, h: 1.1, fontFace: BF, fontSize: 10.5, color: MUTED, margin: 0, valign: "top", isTextBox: true });
s.addNotes("Every mean lies at or below the reference value, as it must: a frozen policy cannot beat the optimum. The perturbation study (a = ±0.02) is still to do.");

// ---- 15. Perturbation -----------------------------------------------------------
s = pres.addSlide();
title(s, "Moving the boundary barely moves the price", "Part 5.3 — case 3, S₀ = 100: shift the NN boundary by aK, cap at U_j, floor at 0");
img(s, "figures/p5_perturbation.png", 0.5, 1.3, 5.6, 992, 544);
const pm = D.pert.find(p => p.a === -0.02), pp2 = D.pert.find(p => p.a === 0.02);
stat(s, `${pm.mean_diff >= 0 ? "+" : ""}${fmt(pm.mean_diff, 3)} $`, `a = −0.02: SE ${fmt(pm.se_diff, 3)}; ${(100 * pm.frac_paths_changed).toFixed(0)}% of paths now exercise later`, 6.35, 1.3, 3.15, ORANGE, 24);
stat(s, `${pp2.mean_diff >= 0 ? "+" : ""}${fmt(pp2.mean_diff, 3)} $`, `a = +0.02: SE ${fmt(pp2.se_diff, 3)}; cap binds on ${pp2.cap_binds_dates} of 360 dates`, 6.35, 2.6, 3.15, BLUE, 24);
s.addText("Only paths that enter the shifted band change decision. The cap absorbs most of an upward shift (applied mean shift " + fmt(pp2.applied_shift_mean, 3) + "K). The NN sits ≈0.04K below the reference, so moving down hurts and moving up lands on the flat part.",
  { x: 6.35, y: 3.9, w: 3.15, h: 1.25, fontFace: BF, fontSize: 10.5, color: MUTED, margin: 0, valign: "top", isTextBox: true });
footer(s, "Dots: the assignment's shifts (95% paired intervals). Line and band: our finer supplementary sweep on the same 50,000 paths.");
s.addNotes("The optimal boundary itself moves by only " + (D.neff[0].E_mean_ref360_vs_ref180 * 100).toFixed(2) + "% of K between N = 180 and 360, 10 to 100 times less than the fitted errors, so changes of a fitted policy with N are learning error.");

// ---- 16. Answer -------------------------------------------------------------------
s = pres.addSlide();
s.background = { color: NAVY };
s.addText("How accurately must the boundary be learned?", { x: 0.6, y: 0.45, w: 8.8, h: 0.7, fontFace: HF, fontSize: 28, bold: true, color: WHITE, margin: 0, isTextBox: true });
[["Less than it looks", "2–8% mean boundary error costs cents: the value is flat near the optimal threshold (smooth pasting)."],
 ["Except where paths go", "a small error at a heavily visited state (case-0 NN at t₀, S₀ = 60) costs 0.87 $."],
 ["Structure beats fitting", "the Part 1 cap gives the pre-dividend boundary exactly; both learners only fill in the rest."],
 ["Selection is noisy", `validation cannot separate checkpoints (all within ~2 SE); no fitted price exceeds the reference (max z = ${D.zmax.toFixed(2)}).`]].forEach(([h, t], i) => {
  const y = 1.45 + i * 0.8;
  badge(s, i + 1, 0.6, y, ORANGE);
  s.addText([{ text: h + "  ", options: { bold: true, color: WHITE } }, { text: t, options: { color: ICE } }],
    { x: 1.2, y: y - 0.08, w: 8.2, h: 0.65, fontFace: BF, fontSize: 14, valign: "middle", margin: 0, isTextBox: true });
});
s.addText("Reference: our own validated grid solver (the supplied reference files were not available); draw order documented in the code.",
  { x: 0.6, y: 4.85, w: 8.8, h: 0.4, fontFace: BF, fontSize: 11, italic: true, color: ICE, margin: 0, isTextBox: true });

pres.writeFile({ fileName: "slides.pptx" }).then(() => console.log("wrote slides.pptx"));
