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
s.addNotes("All reference numbers come from the supplied reference_results.npz; all random draws follow the supplied README conventions. Our own grid solver is used for the Part 1 illustrations and as an independent cross-check.");

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

// ---- helper for Part 1: a card of equation lines ---------------------------
function eqCard(slide, heading, lines, x, y, w, h, size = 13) {
  card(slide, x, y, w, h);
  const runs = [{ text: heading, options: { bold: true, color: NAVY, fontFace: HF, fontSize: size + 2, breakLine: true } }];
  lines.forEach((l, i) => runs.push({ text: l, options: { breakLine: i < lines.length - 1, color: INK } }));
  slide.addText(runs, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: h - 0.2, fontFace: BF, fontSize: size,
    valign: "top", paraSpaceAfter: 5, margin: 0, isTextBox: true });
}
const P1 = (t) => "Part 1 · " + t;

// ---- 3. Part 1: what we explain ---------------------------------------------
s = pres.addSlide();
title(s, "What Part 1 explains", P1("the shape of the exercise boundary in Cox & Rubinstein's Fig. 5-37"));
img(s, "figures/p1_boundaries.png", 0.5, 1.3, 6.2, 1440, 576);
eqCard(s, "Read the plot", [
  "Horizontal axis u = T − t: calendar time advances RIGHT → LEFT.",
  "δ = 0: smooth curve rising to K at maturity.",
  "δ = 1.25%: boundary drops to ≈ 0 just before each dividend (right of each dotted line) …",
  "… rises along a straight line as u grows …",
  "… and jumps UP right after the dividend (left of the line).",
], 6.9, 1.3, 2.6, 3.7, 11);
footer(s, "Our grid solver, N = 360 (solid) and 180 (dashed); it agrees with the supplied reference to ≈1e-3 $ in the boundary.");
s.addNotes("Start here: everything in Part 1 explains these features. Stress the axis direction first; the dividend is paid when calendar time crosses a dotted line from right to left.");

// ---- 4. Item 1 -------------------------------------------------------------------
s = pres.addSlide();
title(s, "Item 1 · Never exercise the put just before the jump", P1("V(d⁻, s) = V(d⁺, (1 − δ)s)"));
eqCard(s, "Argument", [
  "Just before the jump: exercise (K − s)⁺, or hold through it.",
  "No time passes from d⁻ to d⁺ and the put gets no dividend, so holding is worth V(d⁺, (1 − δ)s).",
  "⇒ V(d⁻, s) = max{ (K − s)⁺ , V(d⁺, (1 − δ)s) }.",
  "Exercise just after the jump is always possible:",
  "V(d⁺, (1 − δ)s) ≥ K − (1 − δ)s = (K − s) + δs > K − s.",
  "⇒ the max is always the second term: the identity.",
  "Before vs after: after pays δs more, with no interest lost ⇒ apply the jump, then decide.",
], 0.5, 1.3, 5.0, 3.8, 12);
img(s, "figures/p1_pre_jump_panel1.png", 5.7, 1.3, 3.8, 720, 528);
s.addText("At d₃ the gap V(d⁻,s) − (K − s) equals δs exactly wherever the put is exercised at d⁺ (s ≲ 90).",
  { x: 5.7, y: 4.2, w: 3.8, h: 0.8, fontFace: BF, fontSize: 10.5, color: MUTED, margin: 0, valign: "top", isTextBox: true });
s.addNotes("One-line version: exercising after the drop pays delta times s more, and no time passes, so there is no interest cost. Hence pre-jump exercise is dominated and the code can apply the jump first.");

// ---- 5. Item 2 derivation ----------------------------------------------------
s = pres.addSlide();
title(s, "Item 2 · Why b falls to zero before a dividend", P1("b(d − ε) ≤ K(1 − e^(−rε)) / δ"));
eqCard(s, "Lower bound (wait, then exercise)", [
  "t = d_k − ε, after d_{k−1}: no dividend in (t, d_k).",
  "Strategy: wait until d_k⁺ and exercise. Using (x)⁺ ≥ x and E[S_{d⁻} | S_t = s] = s e^{rε}:",
  "V(t, s) ≥ e^{−rε} E[K − (1 − δ)S_{d⁻}] = K e^{−rε} − (1 − δ)s.",
], 0.5, 1.3, 4.4, 2.1, 12);
eqCard(s, "Cap on the boundary", [
  "If s is in the exercise region, V = K − s, so",
  "K − s ≥ K e^{−rε} − (1 − δ)s  ⇔  δs ≤ K(1 − e^{−rε}).",
  "⇒ b(d − ε) ≤ K(1 − e^{−rε})/δ ≈ K r ε / δ → 0 as ε ↓ 0.",
], 5.1, 1.3, 4.4, 2.1, 12);
eqCard(s, "Same bound on the exercise grid", [
  "d_k = t_{j_d} is itself an exercise date, so 'stop at t_{j_d} after the jump' is an admissible grid stopping time from t_j < t_{j_d}.",
  "The same computation gives the bound with ε = (j_d − j)h.",
], 0.5, 3.6, 9, 1.4, 12);
s.addNotes("Economics: exercising now earns interest on K; waiting captures the drop delta*s. Exercise only pays if delta*s <= K(1-e^{-r eps}). As eps goes to 0 the interest term vanishes, so nothing positive can be exercised.");

// ---- 6. Item 2 consequences ------------------------------------------------------
s = pres.addSlide();
title(s, "Item 2 · What the bound implies", P1("proximity, grid distance, the jump and the maturity limit"));
img(s, "figures/p1_cap_zoom.png", 0.8, 1.2, 8.4, 1600, 528);
const prox = D.proximity.find(p => p.s === 80), prox10 = D.proximity.find(p => p.s === 10);
stat(s, `ε* ≈ δs/(rK)`, `no exercise within ε*(s): ${prox10.eps_star_days.toFixed(0)} days (s=10), ${prox.eps_star_days.toFixed(0)} (s=80)`, 0.5, 4.12, 2.15, ORANGE, 18);
stat(s, "1.63 → 0.81", "cap one step before: > 0 on the grid, → 0 linearly in h", 2.78, 4.12, 2.15, NAVY, 20);
stat(s, "0.69 · 0.75 · 0.89 K", "upward jump just after d₁, d₂, d₃ (calendar time)", 5.06, 4.12, 2.15, NAVY, 16);
stat(s, `→ K`, `after d₃ (no dividend left, r > 0) b → K at maturity`, 7.34, 4.12, 2.15, BLUE, 20);
s.addNotes("Proximity depends on s: for fixed s, delta*s beats K(1-e^{-r eps}) once eps < eps*(s) ~ delta*s/(rK), so smaller prices must be closer to the dividend. The bound is a function of s and eps only, which makes this precise. A positive boundary one grid step before the dividend is compatible with the zero limit because on a grid eps >= h. Near the dividend the boundary sits ON the cap (the bound is attained because exercise at d+ is almost certain for small s): these are the straight lines of slope rK/delta ~ 3.9K per year in Cox-Rubinstein. After the dividend the next one is far away, so the incentive to wait disappears and the boundary jumps up. After d3 the boundary tends to K at maturity, as in the delta = 0 curve of Cox-Rubinstein Fig. 5-37.");

// ---- 7. Item 3 ----------------------------------------------------------------------
s = pres.addSlide();
title(s, "Item 3 · Dividends can only help the put", P1("V₀.₀₁₂₅ ≥ V₀ and b₀.₀₁₂₅ ≤ b₀, with equality from d₃ on"));
const steps = ["Couple: same Brownian increments from (t_j, s): S^δ_i = S⁰_i (1−δ)^{n_ji} ≤ S⁰_i  (n_ji = dividends in (t_j, t_i])",
               "Same information ⇒ same stopping times. Common τ ⇒ (K − S^δ_τ)⁺ ≥ (K − S⁰_τ)⁺ on every path",
               "Take discounted expectations, then sup over τ ⇒ V_δ(t_j, s) ≥ V₀(t_j, s)",
               "If V_δ = K − s then K − s = V_δ ≥ V₀ ≥ K − s ⇒ V₀ = K − s: E_δ ⊆ E₀ ⇒ b_δ ≤ b₀",
               "t_j ≥ d₃ (incl. d₃ at the same post-jump s): no dividend left ⇒ identical problems"];
steps.forEach((t, i) => {
  const y = 1.3 + i * 0.74;
  badge(s, i + 1, 0.5, y);
  s.addText(t, { x: 1.05, y: y - 0.1, w: 4.75, h: 0.62, fontFace: BF, fontSize: 11.5, color: INK,
    valign: "middle", margin: 0, isTextBox: true });
});
stat(s, "0 %", "paths with Q_δ < Q₀ under one common τ (coupled simulation, 20,000 paths)", 6.1, 1.3, 3.4, BLUE, 24);
stat(s, `${(D.mc[1].frac_paths_Qd_lt_Q0 * 100).toFixed(1)} %`, "paths violating it when each model uses its own stopping rule", 6.1, 2.55, 3.4, ORANGE, 24);
stat(s, "A = B = F = 0", "supplied reference, N = 180 and 360 (Checks slide)", 6.1, 3.8, 3.4, NAVY, 24);
s.addNotes("The key step is fixing ONE stopping time for both models before comparing payoffs; the second statistic shows pathwise dominance fails if each model stops by its own rule. Containment does not need the exercise region to be an interval.");

// ---- 8. Item 4 ----------------------------------------------------------------------
s = pres.addSlide();
title(s, "Item 4 · The call must decide before the dividend", P1("C(d⁻, s) = max{ (s − K)⁺ , C(d⁺, (1 − δ)s) }"));
eqCard(s, "Argument", [
  "The jump LOWERS the call's intrinsic value: ((1 − δ)s − K)⁺ ≤ (s − K)⁺.",
  "Exercising just before delivers the cum-dividend stock, i.e. captures the dividend.",
  "⇒ C(d⁻, s) = max{(s − K)⁺, C(d⁺, (1 − δ)s)}, and the max CAN bind (large s).",
  "Implementation: test call exercise BEFORE applying the dividend at d_k.",
  "Put (item 1): same max structure, but the pre-jump term never wins ⇒ jump first is exact.",
], 0.5, 1.3, 5.0, 3.1, 12);
img(s, "figures/p1_pre_jump_panel2.png", 5.7, 1.3, 3.8, 720, 528);
s.addText(`Call at S₀ = 100: decide before the jump ${fmt(D.call[3]["C(0,100)"])} · decide after (put-style) ${fmt(D.call[1]["C(0,100)"])} · European ${fmt(D.call[0]["C(0,100)"])}. Pre-jump thresholds s* = 139.7, 128.8, 104.8.`,
  { x: 0.5, y: 4.5, w: 9, h: 0.6, fontFace: BF, fontSize: 11.5, color: INK, margin: 0, valign: "top", isTextBox: true });
footer(s, "Our grid solver, N = 180, δ = 0.0125. Deciding after the jump makes the call exercise one grid step early, losing interest K(1 − e^(−rh)).");
s.addNotes("Mirror image of item 1: for the put the drop helps, so waiting past it is free; for the call the drop hurts, so the holder may want to exercise just before it.");

// ---- 9. Checks with computed boundaries --------------------------------------------
s = pres.addSlide();
title(s, "Checks · Ordering on the computed boundaries", P1("g_j = b_j^{0.0125} − b_j^0 ; A = #{j < j*: g_j > 1e-8}, B = max (g_j)⁺/K, F = max_{j ≥ j*} |g_j|/K"));
const oh = { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: BF, fontSize: 12 };
const oc = (t) => ({ text: t, options: { fontFace: BF, fontSize: 12, color: INK } });
const orows = [];
[180, 360].forEach(N => ["ref", "LS", "NN"].forEach(m => {
  const r = D.order.find(o => o.N === N && o.method === m);
  orows.push([oc(String(N)), oc(m === "ref" ? "reference" : m), oc(String(Math.round(r.A))), oc(fmt(r.B, 3)), oc(fmt(r.F, 3))]);
}));
s.addTable([["N", "Method", "A", "B", "F"].map(t => ({ text: t, options: oh })), ...orows],
  { x: 0.5, y: 1.35, w: 4.6, colW: [0.7, 1.3, 0.8, 0.9, 0.9], rowH: 0.36,
    border: { type: "solid", pt: 0.5, color: "D5DAE6" }, fill: { color: WHITE } });
bullets(s, [
  "Reference: exactly ordered, A = B = F = 0; max_s (V₀ − V₀.₀₁₂₅)⁺ = 0 at t₀ for both N.",
  "LS: ordered before d₃ (A = 0), but F > 0 after d₃ where the problems are identical: the two fits use different samples → regression/sampling error.",
  "NN: violations only just after d₁ and d₂, where the δ-network overshoots the post-dividend boundary (up to 0.08K).",
  "Fitted methods are not forced to respect item 3, so A, B, F measure LEARNING error, not the model.",
], 5.35, 1.35, 4.15, 3.7, 11.5);
s.addNotes("Only the reference obeys the theorem exactly. The fitted diagnostics tell us where the learning methods are weakest: after d3 for LS, just after dividends for the NN.");

// ---- 6. Part 2: reference verification ---------------------------------------
s = pres.addSlide();
title(s, "Refinement vs changing N", "Part 2 — supplied --verify: precise to ~2e-5 $; changing N changes the problem itself");
const hdr = { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: BF, fontSize: 12 };
const cell = (t, b = false) => ({ text: t, options: { fontFace: BF, fontSize: 12, color: INK, bold: b } });
s.addTable([
  [{ text: "Change", options: hdr }, { text: "Max price change ($)", options: hdr }, { text: "Max boundary change ($)", options: hdr }],
  [cell("Spatial ΔS 0.10 → 0.05"), cell(sci(D.refine.spatial_dv)), cell(sci(D.refine.spatial_db))],
  [cell("Time 16 → 32 substeps"), cell(sci(D.refine.time_dv)), cell(sci(D.refine.time_db))],
  [cell("Our solver vs supplied arrays"), cell(sci(D.refine.own_dv)), cell(sci(D.refine.own_db))],
  [cell("N = 180 → 360", true), cell(sci(D.refine.N_dv), true), cell(fmt(D.refine.N_db, 3), true)],
], { x: 0.5, y: 1.45, w: 5.6, colW: [2.2, 1.7, 1.7], rowH: 0.45, border: { type: "solid", pt: 0.5, color: "D5DAE6" }, fill: { color: WHITE } });
card(s, 6.4, 1.45, 3.1, 2.25);
s.addText([
  { text: "Supplied reference", options: { bold: true, breakLine: true } },
  { text: "reference_solver.py --verify passed: saved arrays match a recomputation (≤ 2e-10). Finite differences, ΔS = 0.05, 32 substeps. Our independent log-grid solver agrees to within the refinement changes." },
], { x: 6.55, y: 1.55, w: 2.8, h: 2.05, fontFace: BF, fontSize: 11, color: INK, valign: "top", margin: 0, isTextBox: true });
stat(s, "≈ 2e-5 $", "reference price precision (largest refinement change)", 0.5, 3.95, 2.7, BLUE);
stat(s, "≈ 0.3 $", "boundary shift from N = 180 → 360: a different problem", 3.4, 3.95, 2.7, ORANGE);
footer(s, "A claimed accuracy gain smaller than the reference's own precision (~2e-5 $ in price, ~2e-3 $ in boundary) cannot be resolved.");
s.addNotes("Time refinement barely moves anything because the kernel integrates the lognormal step exactly. More exercise dates raise the value by ~1e-3 dollars and move the boundary by ~0.3 dollars, two orders of magnitude above the refinement changes.");

// ---- 7. Part 2: simulation ----------------------------------------------------
s = pres.addSlide();
title(s, "Exact simulation passes the martingale check", "Part 2 — (mean S_T − S₀e^(rT)(1−δ)³) / SE on the final S₀ = 100 sample");
D.martingale.forEach((z, i) => stat(s, (z >= 0 ? "+" : "") + z.toFixed(2),
  `case ${i}: N = ${i < 2 ? 180 : 360}, δ = ${i % 2 ? "0.0125" : "0"}`, 0.5 + i * 2.28, 1.45, 2.1, Math.abs(z) > 1.9 ? ORANGE : NAVY));
bullets(s, [
  "Exact lognormal step, dividend applied on arrival at an integer dividend index; a start at a dividend date is post-jump.",
  "Training mixture A (README rule): v, u uniform; A = K·0.001^(1−u) if v < 1/2, else K(0.2 + u).",
  "All four z-scores lie inside ±2; case 2 sits at the edge (1.96), which is plausible for one of four draws.",
  "All banks follow the README draw order and arithmetic: one default_rng per bank, starts then normals, log1p(−δ) before dividend indices.",
], 0.5, 2.9, 9, 2.2, 13);
s.addNotes("Draw order and arithmetic follow the supplied README exactly, so the samples match the instructor run up to floating-point and library differences.");

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
footer(s, "Case 0, date j = 90. Selecting the largest crossing gives one exercise interval (0, b] and discards the spurious continuation pocket around s ≈ 3–34.");
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
footer(s, "Checkpoint 0 was never selected, yet payoff training barely changed the boundary error in cases 0–2 and worsened it in case 3.");
s.addNotes("Validation means differ by less than about 1.3 paired standard errors, so selection is close to picking among equals. The value is flat near the optimal threshold, so validation barely reacts to boundary changes.");

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
  "Left = after d₃: no dividend remains and the boundary rises to K; LS is ~0.12K low, the NN only ~0.02K.",
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
s.addText("S₀ = 60 omitted: every policy exercises at once (value 40) except the case-3 NN, which loses 0.045 $ there. Smooth pasting makes price error roughly second order in boundary error.",
  { x: 6.35, y: 4.0, w: 3.15, h: 1.1, fontFace: BF, fontSize: 10.5, color: MUTED, margin: 0, valign: "top", isTextBox: true });
s.addNotes("Every mean lies at or below the reference value, as it must: a frozen policy cannot beat the optimum. The perturbation study (a = ±0.02) is still to do.");

// ---- 15. Perturbation -----------------------------------------------------------
s = pres.addSlide();
title(s, "Too early costs, a bit later is free", "Part 5.3 — case 3, S₀ = 100: shift the NN boundary by aK, cap at U_j, floor at 0");
img(s, "figures/p5_perturbation.png", 0.5, 1.3, 5.6, 992, 544);
const pm = D.pert.find(p => p.a === -0.02), pp2 = D.pert.find(p => p.a === 0.02);
stat(s, `${pm.mean_diff >= 0 ? "+" : ""}${fmt(pm.mean_diff, 3)} $`, `a = −0.02: SE ${fmt(pm.se_diff, 3)}; ${(100 * pm.frac_paths_changed).toFixed(0)}% of paths now exercise later`, 6.35, 1.3, 3.15, BLUE, 24);
stat(s, `${pp2.mean_diff >= 0 ? "+" : ""}${fmt(pp2.mean_diff, 3)} $`, `a = +0.02: SE ${fmt(pp2.se_diff, 3)}; cap binds on ${pp2.cap_binds_dates} of 360 dates`, 6.35, 2.6, 3.15, ORANGE, 24);
s.addText("Only paths entering the shifted band change decision; the cap absorbs much of an upward shift (applied mean shift " + fmt(pp2.applied_shift_mean, 3) + "K). The NN overshoots just after d₁, so exercising earlier hurts and waiting slightly longer helps.",
  { x: 6.35, y: 3.9, w: 3.15, h: 1.25, fontFace: BF, fontSize: 10.5, color: MUTED, margin: 0, valign: "top", isTextBox: true });
footer(s, "Dots: the assignment's shifts (95% paired intervals). Line and band: our finer supplementary sweep on the same 50,000 paths.");
s.addNotes("The optimal boundary itself moves by only " + (D.neff[0].E_mean_ref360_vs_ref180 * 100).toFixed(2) + "% of K between N = 180 and 360, far less than the fitted errors, so changes of a fitted policy with N are learning error.");

// ---- 16. Answer -------------------------------------------------------------------
s = pres.addSlide();
s.background = { color: NAVY };
s.addText("How accurately must the boundary be learned?", { x: 0.6, y: 0.45, w: 8.8, h: 0.7, fontFace: HF, fontSize: 28, bold: true, color: WHITE, margin: 0, isTextBox: true });
[["Less than it looks", "2–7% mean boundary error costs cents to ~0.25 $: the value is flat near the optimal threshold (smooth pasting)."],
 ["Where paths decide", "errors matter where paths cross the boundary: the case-3 NN has the smaller max error but the larger price loss."],
 ["Structure beats fitting", "the Part 1 cap gives the pre-dividend boundary exactly; both learners only fill in the rest."],
 ["Selection is noisy", `validation cannot separate checkpoints (all within ~2 SE); no fitted price exceeds the reference (max z = ${D.zmax.toFixed(2)}).`]].forEach(([h, t], i) => {
  const y = 1.45 + i * 0.8;
  badge(s, i + 1, 0.6, y, ORANGE);
  s.addText([{ text: h + "  ", options: { bold: true, color: WHITE } }, { text: t, options: { color: ICE } }],
    { x: 1.2, y: y - 0.08, w: 8.2, h: 0.65, fontFace: BF, fontSize: 14, valign: "middle", margin: 0, isTextBox: true });
});
s.addText("Reference: supplied reference_results.npz (--verify passed); draws follow the supplied README; our own solver agrees to ~1e-5 $.",
  { x: 0.6, y: 4.85, w: 8.8, h: 0.4, fontFace: BF, fontSize: 11, italic: true, color: ICE, margin: 0, isTextBox: true });

pres.writeFile({ fileName: "../slides.pptx" }).then(() => console.log("wrote ../slides.pptx"));   // deliverable at the repo root
