"""Minimal D2-a recovery QA; no uniform-risk/first-success claim.

Numerical comparison identities use the recovered original model. Projection
KKT, calendar indexing and direction scales are checked exactly. Archive source
and inputs remain untouched. Every structural candidate is retained in a CSV.
"""
from pathlib import Path
from fractions import Fraction as F
import csv
import hashlib
import json
import sys
import time
import types
import importlib.util
sys.dont_write_bytecode = True

from d2a_core import (GRID, B, RATE, ETA, XI, K, PREFIX, L, calendar,
                      all_members, terminal, fixed, normalize_raw)

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "work/r1_extract/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919"
if sys.platform == "win32":
    # Keep extended paths in __file__ so inherited modules' nested sys.path
    # entries remain usable by Windows importlib, without changing their code.
    R = Path(chr(92)*2 + "?" + chr(92) + str(R.resolve()))
protocol_bytes = (ROOT / "work/d2a_PROTOCOL_v1.json").read_bytes()
protocol = json.loads(protocol_bytes)
protocol_hash = hashlib.sha256(protocol_bytes).hexdigest()
assert protocol_hash == (ROOT / "work/d2a_PROTOCOL_v1.sha256").read_text().strip()

import numpy as np
import scipy
sys.path.insert(0, str(R / "frozen"))
import validate_sharp as original
from projection import solve, rational_certificate
# The inherited packages repeatedly use unqualified `input_setup` and `context`
# module names. Bind only the three documented data paths needed by the numeric
# calendar module, rather than mixing two different inherited package contexts
# in one process. Its source file is executed unmodified.
Cal = R / "input/CERTO_FDI_STAGE_D1_CALENDAR_RISK_20260919"
Hold = Cal / "input/CERTO_FDI_STAGE_D1_NONLINEAR_ADMISSION_20260919/input/CERTO_FDI_STAGE_D1_ENTRY_LTV_20260913/input/CERTO_FDI_STAGE_D1_HOLD_REDESIGN_20260912"
numeric_context = types.ModuleType("context")
numeric_context.ROOT = Cal
numeric_context.BASE = Hold / "input/CERTO_FDI_STAGE_D1_ROBUST_HOLD_20260912"
numeric_context.INP = numeric_context.BASE / "input/CERTO_FDI_STAGE_D1_READOUT_20260911"
previous_context = sys.modules.get("context")
sys.modules["context"] = numeric_context
spec = importlib.util.spec_from_file_location("d2a_inherited_calendar_model", Cal / "src/calendar_model.py")
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)
if previous_context is None:
    del sys.modules["context"]
else:
    sys.modules["context"] = previous_context
sys.path.insert(0, str(R / "src"))
from event_accounting import budget

def check_inventory():
    members = list(all_members())
    for item in members:
        H, family, S = item["H_post_slots"], item["family"], item["stage_endpoint"]
        assert not item["validation_errors"], item
        if family == "terminal_balanced":
            mine = terminal(H)
            old = original.schedule(H, K, float(XI))
            assert mine[0] == old[0].tolist() and mine[1] == old[1].tolist()
        elif family.startswith("fixed"):
            mine = fixed(H, int(family[5:]))
            old = original.fixed(H, int(family[5:]), K)
            assert mine[0] == old[0].tolist() and mine[1] == old[1].tolist()
        elif family == "switch_then_stay":
            mine = terminal(S)
            old = original.schedule(S, K, float(XI))
            assert mine[0] == old[0].tolist() and mine[1] == old[1].tolist()
        for observation in item["observations"]:
            assert observation["point_index"] + 1 == observation["average_indices"][1]
            assert observation["average_indices"][1] - observation["average_indices"][0] == 250
            if not observation["source_segment"]:
                assert observation["hold_start_age_steps"] >= 1500
                assert observation["point_hold_age_steps"] >= 1749
    path = ROOT / "work/d2a_calendar_inventory.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        names = ["readout", "H_post_slots", "elapsed_seconds", "family", "stage_endpoint",
                 "transfers", "completed_symmetric_blocks", "readings", "physical_contract",
                 "direction_status", "uniform_mean_status", "uniform_variance_status", "risk_status"]
        writer = csv.DictWriter(stream, fieldnames=names)
        writer.writeheader()
        for readout in protocol["readouts"]:
            for item in members:
                writer.writerow({"readout":readout, "H_post_slots":item["H_post_slots"],
                    "elapsed_seconds":item["elapsed_seconds"], "family":item["family"],
                    "stage_endpoint":item["stage_endpoint"], "transfers":len(item["moves"]),
                    "completed_symmetric_blocks":item["completed_symmetric_blocks"],
                    "readings":len(item["observations"]),
                    "physical_contract":"INHERITED_RULES_CHECKED" if not item["validation_errors"] else ";".join(item["validation_errors"]),
                    "direction_status":"NOT_RUN", "uniform_mean_status":"NOT_RUN",
                    "uniform_variance_status":"NOT_RUN", "risk_status":"NOT_RUN"})
    return {"calendar_members":len(members), "readout_calendar_rows":2*len(members),
            "inherited_generation_identity":"PASS", "physical_rule_failures":0,
            "first_post_point_age":min(o["point_hold_age_steps"] for m in members for o in m["observations"] if not o["source_segment"]),
            "maximum_elapsed_seconds":max(float(F(m["elapsed_seconds"])) for m in members)}

def direction(item, readout):
    observations = item["observations"]
    nodes = [o["relative_node"] for o in observations]
    tasks = [o["task"] for o in observations]
    signal = [F(0) if j <= 0 else e * ETA * (j - (F(1,2) if readout == "average250" else 0))
              for j,e in zip(nodes,tasks)]
    _, edge, pin, iterations = solve(list(map(float,signal)), nodes, float(B), float(RATE))
    exact = rational_certificate(signal, nodes, B, RATE, edge, pin)
    raw = [s-F(z) for s,z in zip(signal,exact["z"])]
    result = normalize_raw(raw, tasks)
    if result is None:
        return {"status":"ZERO_DIRECTION" if not any(raw) else "ROUNDED_DIRECTION_DEGENERATE", "iterations":iterations,
                "projection_objective":exact["objective"], "kkt_exact":"PASS"}, None
    assert result["direction_norm_squared"] <= 1
    # Exact raw projection support identity is also checked independently.
    dual = sum((abs(F(q))*RATE*(nodes[i+1]-nodes[i]) for i,q in enumerate(exact["q"])), F(0))
    dual += B * sum((abs(F(e)) for e in exact["eta"]), F(0))
    assert dual == sum((v*F(z) for v,z in zip(raw,exact["z"])), F(0))
    assert sum((v*s for v,s in zip(raw,signal)), F(0)) - dual == result["raw_norm_squared"]
    summary = {"status":"EXACT_NODAL_DIRECTION_QA_PASS", "iterations":iterations,
               "projection_objective":exact["objective"], "kkt_exact":"PASS",
               "raw_projection_support":str(dual), "raw_gap_squared":str(result["raw_norm_squared"]),
               "direction_norm_squared":str(result["direction_norm_squared"]),
               "normalizer":str(result["normalizer"]),
               "raw_zero_moment_preserved":result["exact_zero_moment_preserved"],
               "rounding_l1":str(result["rounding_l1"]),
               "zero_direction_is_not_full_experiment_impossibility":True}
    return summary, np.array(list(map(float,result["physical"])))

def point_block(A,B,C,D):
    """Last pre-step observation after 249 unread state transitions."""
    before = cm.block_noise(A,B,C,D,False,L=249)
    transition = np.eye(19)
    transition[:18,:18] = A
    transition[18,:18] = C
    noise = np.vstack((B,D[None,:]))
    S = cm.Q*(noise@noise.T)
    S[18,18] += cm.R
    initial = np.zeros((19,19)); initial[:18,:18] = before["Q"]
    joint = transition@initial@transition.T+S
    state_transition = A@before["A"]
    return {"A":state_transition, "C":C@before["A"], "Q":joint[:18,:18],
            "U":joint[:18,18], "V":joint[18,18], "noise_joint":joint}

def numerical(item, readout, physical):
    beta = 0.0
    A,Bn,C,D,E0,E1 = cm.hold(beta)
    Am,Bm = cm.move()
    nohold = cm.block_noise(A,Bn,C,D,False)
    nomove = cm.block_noise(Am,Bm,C,D,False)
    reading = cm.block_noise(A,Bn,C,D,True) if readout == "average250" else point_block(A,Bn,C,D)
    readmap = {o["slot_zero_based"]:o for o in item["observations"]}
    blocks, details = [], []
    for slot in range(item["T_fast_steps"]//250):
        start = slot*250
        move_index = next((i for i,(a,b) in enumerate(item["moves"]) if a<=start<b),None)
        if move_index is None:
            completed = sum(b<=start for a,b in item["moves"])
            parity = 1 if completed%2==0 else -1
            read = slot in readmap
            kind, block = ("hold",reading) if read else ("settle",nohold)
            local = 0
        else:
            read, kind, block = False,"move",nomove
            parity = 1 if move_index%2==0 else -1
            local = start-item["moves"][move_index][0]
        blocks.append((kind,read,block)); details.append((parity,local))
    Gamma,_ = cm.cov_forward(blocks)
    second = cm.cov_all_block_innovations(blocks)
    weights = np.zeros(item["T_fast_steps"])
    for o,value in zip(item["observations"],physical):
        if readout == "average250":
            lo,hi = o["average_indices"]; weights[lo:hi] = value/250
        else:
            weights[o["point_index"]] = value
    ell = np.zeros(18); fast_variance = 0.0
    for n in range(item["T_fast_steps"]-1,-1,-1):
        moving = blocks[n//250][0] == "move"
        AA,BB = (Am,Bm) if moving else (A,Bn)
        g = BB.T@ell+D*weights[n]
        fast_variance += cm.Q*(g@g)+cm.R*weights[n]**2
        ell = AA.T@ell+C*weights[n]
    variance = float(physical@Gamma@physical)
    covariance_error = float(abs(Gamma-second).max())
    variance_error = abs(variance-fast_variance)
    assert covariance_error < 1e-11 and variance_error < 1e-11
    # Direct fast mean vs homogeneous-clock block mean, no statistical reset.
    ref = cm.reference_forcing(); _,gp,_ = cm.inputs(); ef = np.eye(6)[:,3]
    fast_state = np.zeros((18,2)); block_state = np.zeros((18,2)); ys=[]; yb=[]
    lifts={}
    onset,kappa=1.0,0.0003
    for parity in (-1,1):
        for hypothesis in (0,1):
            for ramp in (False,True):
                Fm=np.eye(21); Fm[:18,:18]=A
                Fm[:18,18]=E0@ef*kappa*hypothesis*ramp
                Fm[:18,19]=E0@(parity*beta*gp)+E1@ef*kappa*hypothesis*ramp-E0@ef*kappa*hypothesis*ramp*onset
                Fm[18,19]=.001
                if readout=="average250":
                    Fm[20,:18]=C/250
                    lifts[parity,hypothesis,ramp]=np.linalg.matrix_power(Fm,250)
                else:
                    first=np.linalg.matrix_power(Fm,249)
                    last=Fm.copy(); last[20,:18]=C
                    lifts[parity,hypothesis,ramp]=last@first
    for slot,((kind,read,_),(parity,local)) in enumerate(zip(blocks,details)):
        value=np.zeros(2)
        for j in range(250):
            t=(slot*250+j)*.001
            if kind=="move":
                fast_state=Am@fast_state+parity*ref[local+j,:,None]
            else:
                if readout=="average250":value+=C@fast_state/250
                elif j==249:value=C@fast_state
                fast_state=A@fast_state+(E0@(parity*beta*gp))[:,None]
                if t>=onset:
                    fast_state[:,1]+=E0@ef*kappa*(t-onset)+E1@ef*kappa
        blockvalues=[]
        for hypothesis in (0,1):
            if kind=="move":
                for j in range(250):
                    block_state[:,hypothesis]=Am@block_state[:,hypothesis]+parity*ref[local+j]
                blockvalues.append(0.0)
            else:
                vector=lifts[parity,hypothesis,slot*.25>=onset]@np.r_[block_state[:,hypothesis],slot*.25,1.0,0.0]
                block_state[:,hypothesis]=vector[:18]; blockvalues.append(vector[-1])
        if read:ys.append(value); yb.append(blockvalues)
    mu=np.array(ys); mub=np.array(yb)
    mean_error=float(abs(mu-mub).max())
    assert mean_error < 1e-9
    static_sample = np.array([kappa*max(0,float(F(o["sample_average_time_s"] if readout=="average250" else o["point_sample_time_s"]))-onset) for o in item["observations"]])
    sensor = cm.R*float(weights@weights)
    assert variance>=sensor*(1-1e-12)
    if readout=="point_last_fast_read":
        assert abs(sensor-cm.R*float(physical@physical))<1e-15
    else:
        assert abs(sensor-cm.R*float(physical@physical)/250)<1e-15
    return {"beta_parameter_point":beta, "nominal_variance":variance,
            "sensor_variance_exact_float":sensor,
            "fast_adjoint_variance_error":variance_error,
            "forward_vs_all_innovation_covariance_error":covariance_error,
            "fast_vs_block_mean_error":mean_error,
            "nominal_mean_H0":float((physical@mu)[0]),
            "nominal_mean_H1":float((physical@mu)[1]),
            "sampled_static_ramp_signal":float(physical@static_sample),
            "mean_transfer_difference_from_sampled_static_signal":float((physical@mu)[1]-(physical@mu)[0]-physical@static_sample),
            "wrong_diagonal_variance":float(physical@np.diag(np.diag(Gamma))@physical),
            "full_history_no_reset":True, "parameter_point_is_not_uniform_certificate":True}

def main():
    start=time.perf_counter()
    inventory=check_inventory(); rows=[]
    for H,family in [(40,"stay"),(120,"terminal_balanced"),(300,"terminal_balanced")]:
        item=calendar(H,family)
        for readout in protocol["readouts"]:
            summary,physical=direction(item,readout)
            row={"H_post_slots":H,"family":family,"readout":readout,
                 "elapsed_seconds":item["elapsed_seconds"],"transfers":len(item["moves"]),
                 "completed_symmetric_blocks":item["completed_symmetric_blocks"],"direction":summary,
                 "event_failure_per_hypothesis":float(budget(item["T_fast_steps"],len(item["moves"]))["total_failure"]),
                 "uniform_variance_status":"NOT_GENERATED", "uniform_mean_status":"NOT_GENERATED",
                 "risk_status":"NO_NEW_UNIFORM_RISK_CERTIFICATE"}
            if physical is not None:row["numerical_QA"]=numerical(item,readout,physical)
            rows.append(row)
            print("SMOKE",H,family,readout,summary["status"], flush=True)
    receipt=json.loads((ROOT/"work/d2a_extraction_receipt.json").read_text())
    # Imports must not mutate scientific source or inherited inputs.
    unchanged=0
    for name,expected in receipt["file_sha256"].items():
        path=ROOT/"work/r1_extract"/name
        if sys.platform == "win32":
            path=Path(chr(92)*2 + "?" + chr(92) + str(path.resolve()))
        value=hashlib.sha256(path.read_bytes()).hexdigest()
        assert value==expected,name
        unchanged+=1
    result={"protocol_sha256":protocol_hash,"status":"PASS_RECOVERY_QA_ONLY",
            "inventory":inventory,"rows":rows,"original_extracted_files_unchanged":unchanged,
            "python":sys.version,"numpy":np.__version__,"scipy":scipy.__version__,
            "elapsed_wall_seconds":time.perf_counter()-start,
            "full_R1_verifier_rerun":False,"D2a_full_certification_scan":False,
            "source_point_uniform_mean_extension_still_required":True,
            "all_new_actual_direction_uniform_variance_certificates_still_required":True}
    (ROOT/"work/d2a_smoke_results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":result["status"],"inventory":inventory,"elapsed_wall_seconds":result["elapsed_wall_seconds"],"unchanged":unchanged},ensure_ascii=False))

if __name__=="__main__":main()
