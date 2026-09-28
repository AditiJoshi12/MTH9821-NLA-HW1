"""deck_data.py -- export the numbers the slide deck shows (from tables/) to deck_data.json."""
import json, pandas as pd
T = lambda f: pd.read_csv(f"tables/{f}.csv")
ref = T("p2_reference_refinement"); mx = ref.groupby("refinement")[["dV_spots", "db"]].max()
p = T("p5_prices"); pair = T("p5_paired"); e = T("p5_boundary_errors"); sm4 = T("p4_summary"); v4 = T("p4_validation")
d = dict(
  martingale=[round(z, 2) for z in T("p2_martingale").z],
  refine=dict(spatial_dv=T("p2_supplied_verify").spatial_dV_max.max(),
              spatial_db=T("p2_supplied_verify").spatial_db_max.max(),
              time_dv=T("p2_supplied_verify").temporal_dV_max.max(),
              time_db=T("p2_supplied_verify").temporal_db_max.max(),
              own_dv=T("p2_own_vs_supplied").dV_max.max(),
              own_db=T("p2_own_vs_supplied").db_max.max(),
              N_dv=float(T("p2_N_change")[["dV(80)","dV(100)"]].abs().values.max()),
              N_db=float(T("p2_N_change").max_db.max())),
  ls_diag=T("p3_ls_diagnostics")[["case","N","delta","fallback_count","multi_crossing_count","capped_count","replay_max_abs_diff"]].to_dict("records"),
  prices=[dict(case=int(r.case), N=int(r.N), delta=r.delta, S0=int(r.S0), ref=r.ref_value,
               ls=r["mean"], se=r.se,
               nn=float(p[(p.case==r.case)&(p.S0==r.S0)&(p.method=="NN")]["mean"].iloc[0]),
               nnse=float(p[(p.case==r.case)&(p.S0==r.S0)&(p.method=="NN")].se.iloc[0]))
          for _, r in p[p.method=="LS"].iterrows()],
  paired=[dict(case=int(r.case), S0=int(r.S0), pair=r.pair, diff=r.mean_diff, se=r.se) for _, r in pair.iterrows()],
  errors=e[["case","method","E_mean","E_max"]].to_dict("records"),
  nn_summary=sm4[["case","val_mean_ckpt0","selected_checkpoint","val_mean_selected"]].to_dict("records"),
  nn_E=[dict(case=int(c), ckpt0=float(v4[(v4.case==c)&(v4.checkpoint==0)].E_mean_vs_ref.iloc[0]),
             selected=float(v4[(v4.case==c)&(v4.selected)].E_mean_vs_ref.iloc[0])) for c in range(4)],
  mc=T("e3_coupled_mc").to_dict("records"),
  order=T("p1_ordering_checks").dropna().to_dict("records"),
  proximity=T("e2_proximity").to_dict("records"),
  maturity=T("e2_maturity_limit").to_dict("records"),
  pert=T("p5_perturbation").to_dict("records"),
  neff=T("p5_N_effect").to_dict("records"),
  zmax=float(T("p5_prices").query("method in ['LS','NN']").z_vs_ref.max()),
  call=T("e4_call_orderings").to_dict("records"),
)
json.dump(d, open("deck_data.json", "w"), indent=1, default=float)
print("ok")
