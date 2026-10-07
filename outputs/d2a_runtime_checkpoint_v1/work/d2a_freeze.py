"""Freeze declared choices and input identities before numerical smoke checks."""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import json
from d2a_core import GRID, B, RATE, XI

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "work/r1_extract/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919"
old = json.loads((R / "input/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919/audit/DIRECTIONAL_RISK_CERTIFICATE.json").read_text())
document = {
    "protocol_version": "D2-a v1 / 2026-10-07",
    "archive_sha256": "f703091ace28d9017d0400e07984f4c34f03d5efdba14742f5a3a9f4ea94a60b",
    "omega": "40", "omega_f": "200", "h": "1/1000", "delta": "1/4",
    "fast_reads_per_slot": 250, "k_slots": 12, "move_fast_steps": 1500,
    "settle_fast_steps": 1500, "minimum_postarrival_steps_before_removing": 1750,
    "physical_class": {"beta_radius_kg": "1/50", "beta_rate_kg_per_s": "1/1000",
                       "fault_radius_Nm": "3/4", "fault_rate_Nm_per_s": "3/1000"},
    "noise": {"encoder_variance": "(2*pi/2^17)^2/12 using inherited certified pi endpoints",
              "transducer_variance_per_fast_read": "1/10000", "raw_innovations_independent": True},
    "selected_joint_one_based": 4, "healthy_prefix_slots": 4,
    "fault_onset_s": "1", "fault_slope_Nm_per_s": "3/10000",
    "fault_formula": "f(t)=3/10000*max(t-1,0)",
    "H_post_slots": list(GRID),
    "H_units": "post-onset slots; elapsed physical seconds=(H+4)/4",
    "readouts": {
        "point_last_fast_read": {"indices": "n=250*(s+1)-1", "sample_time": "n/1000",
                                 "available_time": "(n+1)/1000", "design_template": "task*eta*j"},
        "average250": {"indices": "n=250*s,...,250*s+249", "weight_each": "1/250",
                       "available_time": "(s+1)/4", "design_template": "task*eta*(j-1/2)"}},
    "direction_nodal_class": {"B": str(B), "rate_per_slot": str(RATE), "eta": "3/40000",
                              "times": "relative nodes -3,-2,-1,0 followed by retained post nodes",
                              "role": "proposal only; actual path mean supports separately certified"},
    "calendar_families": ["stay", "fixed20", "fixed40", "fixed76", "terminal_balanced", "switch_then_stay"],
    "terminal_balanced": {"xi_exact": str(XI), "n_ell": "2*ceil(xi*ell/2)",
        "accept_block": "used+2*(n_ell+k)<=stage horizon",
        "spread_rule": "q,rem=divmod((H-used)//4,number_of_blocks); n_i+=2*q+2*(i<rem)",
        "within_block": "+ for n/2 reads; gap k; - for n reads; gap k; + for n/2 reads",
        "tail": "all remaining slots read at task +"},
    "fixed_tail_rule": "After n held reads: if remaining<=k, read all remaining at current task; else gap k and flip. Last hold may be truncated.",
    "switch_then_stay_endpoints": "all S=20,40,...,floor(H/20)*20, inclusive H when on grid; run terminal_balanced(S), then stay + to H",
    "family_choice": "keep every endpoint candidate; select lowest H with any certified member; at fixed H largest certified power lower bound, then smallest S; do not discard duplicate calendars",
    "direction_rule": "Exact KKT certificate for nodal closest-pair residual; nearest-even round at 1e-12; restore zero moment at last nonzero entry only if exact raw moment is zero; divide by rational sqrt-upper of rounded squared norm to 1e-18; task-transform to physical direction. Zero residual is a direction-certificate failure.",
    "error_radii": {"average_source": old["eps_source"], "average_postmove": old["eps_after_move"],
                    "point_source": "106681889909401270803434156502238755741426225171/25000000000000000000000000000000000000000000000000",
                    "point_postmove": "3399888498583189/1000000000000000000"},
    "point_postmove_scope": "point hold age>=1500 in inherited horizon/event; first admitted slot last sample age1749; no shortening of 1750-step re-move requirement",
    "means": "same comparator under each hypothesis; whole beta path support with real time gaps; two independent nuisance paths; exact sampled ramp values; source/post dynamic corrections distinct; point mean-transfer extension requires its own certificate",
    "event_budget": "delta_j=(N+1)*p_nu+[N-1500*M+(M+1)]*p_X+M*p_E, per hypothesis; N+1 is inherited conservative cap count, not an added point read",
    "variance": "full innovation history; moves and settle have output weights zero but propagate state/innovations; actual direction degree-8 polynomial-Abel certificate; Vminus and Vplus; Vplus/own_certified_Vnominal<=1.01 acceptance rule",
    "risk": {"alpha_strict": "1/1000", "miss_target": "1/10", "null_quantile_rational": "25/8",
             "threshold": "mu0_upper+b0+(25/8)*sqrt_upper(V0plus)",
             "alternative_gap": "mu1_lower-b1-threshold", "power_positive_gap": "1-Mills_upper(gap/sqrt_upper(V1plus))-delta1",
             "negative_gap": "power lower bound 0 unless a valid lower-variance tail certificate is provided; no Vplus substitution",
             "zero_direction": "no separation certificate; randomized alpha test only as a labeled fixed-detector control, no full-experiment impossibility claim"},
    "diagnostic": "translation-invariant signal/health/dynamic/two-sided remainder/two-sided noise budgets; iid predictions are references only",
    "failure_ledger": ["PHYSICAL_CONTRACT_FAILED", "ZERO_DIRECTION", "PROJECTION_CERTIFICATE_FAILED",
                       "MEAN_CERTIFICATE_MISSING_OR_FAILED", "VARIANCE_CERTIFICATE_MISSING_OR_FAILED",
                       "VARIANCE_RATIO_TARGET_NOT_MET", "EVENT_BUDGET_EXHAUSTED", "RISK_TARGET_NOT_MET"],
    "interpretation": "first success only in declared grid and finite family; no continuous minimum, no minimax claim, no sequential false-alarm interpretation",
    "full_scan_status_at_freeze": "NOT_RUN",
}
payload = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
destination = ROOT / "work/d2a_PROTOCOL_v1.json"
destination.write_bytes(payload)
digest = hashlib.sha256(payload).hexdigest()
(ROOT / "work/d2a_PROTOCOL_v1.sha256").write_text(digest + "\n", encoding="ascii")
print("PROTOCOL_SHA256", digest)

manifest = json.loads((R / "MANIFEST_SHA256.json").read_text())
receipt = json.loads((ROOT / "work/d2a_extraction_receipt.json").read_text())
bad = [name for name, value in manifest.items()
       if receipt["file_sha256"].get(R.name + "/" + name.replace("\\", "/")) != value]
assert not bad, bad
print("ROOT_MANIFEST_MATCHES", len(manifest))
