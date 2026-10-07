"""Separate standard-library verification of a saved new D2-a case.

Run with python -S. No NumPy/SciPy, floating optimizer, or old fixed-direction
risk is used. The full integer/Fraction/interval variance witness is rechecked.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import hashlib
import json
import sys
import time
sys.dont_write_bytecode=True
import d2a_cert_case as core
from d2a_core import normalize_raw,calendar,B,RATE,ETA

def verify_projection(document):
    y,t,z,q,eta=[list(map(F,document[k])) for k in ("y","t","z","q","eta")]
    box,rate=F(document["B"]),F(document["R"])
    assert box==B and rate==RATE
    n=len(y);assert len(t)==len(z)==len(eta)==n and len(q)==n-1
    for i in range(n):
        assert abs(z[i])<=box
        assert eta[i]*(z[i]-(box if eta[i]>0 else -box))==0
        assert z[i]-y[i]+(q[i-1] if i else 0)-(q[i] if i<n-1 else 0)+eta[i]==0
    for i in range(n-1):
        difference=z[i+1]-z[i];bound=rate*(t[i+1]-t[i]);assert bound>0
        assert abs(difference)<=bound and q[i]*difference==abs(q[i])*bound
    raw=[a-b for a,b in zip(y,z)]
    assert sum((a*a for a in raw),F(0))/2==F(document["objective"])
    return raw

def main():
    started=time.perf_counter()
    parser=argparse.ArgumentParser();parser.add_argument("--case-dir",required=True)
    args=parser.parse_args();out=Path(args.case_dir).resolve()
    out.relative_to((core.ROOT/"work").resolve())
    pr=core.read_json(out/"ACTUAL_PROTOCOL.json")
    result=core.read_json(out/"CASE_RESULT.json")
    saved_direction=core.read_json(out/"DIRECTION.json")
    projection=core.read_json(out/"PROJECTION_CERTIFICATE.json")
    assert result["protocol_sha256"]==pr["protocol_sha256"]==core.PROTOCOL_SHA
    item=pr["calendar"]
    assert item==calendar(item["H_post_slots"],item["family"],item["stage_endpoint"])
    assert not item["validation_errors"]
    obs=item["observations"];readout=pr["readout"]
    expected=[F(0) if o["relative_node"]<=0 else o["task"]*ETA*(o["relative_node"]-(F(1,2) if readout=="average250" else 0)) for o in obs]
    assert list(map(F,projection["y"]))==expected
    assert list(map(F,projection["t"]))==[F(o["relative_node"]) for o in obs]
    raw=verify_projection(projection)
    direction=normalize_raw(raw,[o["task"] for o in obs]);assert direction is not None
    direction["iterations"]=saved_direction["iterations"]
    nodes=[o["relative_node"] for o in obs]
    direction["dual_support"]=sum((abs(F(q))*RATE*(nodes[i+1]-nodes[i]) for i,q in enumerate(projection["q"])),F(0))+B*sum((abs(F(e)) for e in projection["eta"]),F(0))
    assert core.serial(direction)==saved_direction
    assert core.actual_protocol(item,readout,direction)==pr
    adapter=core.bind_actual(pr,out,result["case"])
    covariance=adapter.certify(True)
    assert core.serial(covariance)==result["uniform_variance"]
    mean=core.mean_certificate(item,readout,direction)
    mean_serial=core.serial(mean)
    # A review-binding field may arrive between generation and this separate
    # verifier. Mathematical payload must be unchanged, metadata is rebound
    # explicitly after the full variance and all derived quantities pass.
    strip=lambda value:{k:v for k,v in value.items() if k!="independent_mean_math_review"}
    assert strip(mean_serial)==strip(result["uniform_mean"])
    events=core.budget(item["T_fast_steps"],len(item["moves"]))
    assert core.serial(events)==result["event_accounting"]
    risk=core.guarded_risk(mean["mean_H0_upper"],mean["mean_H1_lower"],mean["error_H0"],mean["error_H1"],covariance["variance_lower"],covariance["variance_upper"],events["total_failure"])
    assert core.serial(risk)==result["protected_risk"]
    canonical_status,canonical_failures=core.target_classification(covariance,risk)
    assert result.get("arithmetic_risk_target_status",result["status"])==canonical_status
    assert result["failure_classification"]==canonical_failures
    assert result["status"] in ("PENDING_SHARED_MEAN_REVIEW",canonical_status)
    assert "numpy" not in sys.modules and "scipy" not in sys.modules
    prior_case=(out/"CASE_RESULT.json").read_bytes()
    prior_hash=hashlib.sha256(prior_case).hexdigest()
    accepted=mean["independent_mean_math_review"]["status"]=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN"
    if mean_serial!=result["uniform_mean"] or result.get("shared_mean_review_status")!=mean["independent_mean_math_review"]["status"]:
        history=out/"audit"/f"PRIOR_CASE_RESULT_{prior_hash}.json"
        if not history.exists():history.write_bytes(prior_case)
        result.update(uniform_mean=mean_serial,
                      independent_mean_math_review=mean_serial["independent_mean_math_review"],
                      shared_mean_review_status=mean["independent_mean_math_review"]["status"],
                      new_point_mean_algebra_requires_independent_review=not accepted)
        if accepted:result["status"]=canonical_status
        core.atomic_text(out/"CASE_RESULT.json",json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        summary=core.read_json(out/"SUMMARY.json")
        summary.update(status=result["status"],shared_mean_review_status=result["shared_mean_review_status"],
                       independent_mean_math_review=result["independent_mean_math_review"])
        core.atomic_text(out/"SUMMARY.json",json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    receipt={"status":"PASS_STDLIB_NEW_CASE_VERIFIER","case":result["case"],
             "protocol_sha256":core.PROTOCOL_SHA,"numpy_loaded":False,"scipy_loaded":False,
             "projection_KKT_exact":True,"actual_protocol_exact":True,"integer_interval_recursions_rechecked":True,
             "Abel_and_supersolutions_rechecked":True,"uniform_mean_event_risk_recomputed":True,
             "case_result_sha256":hashlib.sha256((out/"CASE_RESULT.json").read_bytes()).hexdigest(),
             "prior_case_result_sha256_before_review_binding":prior_hash,
             "scientific_target_status":result["status"],"independent_point_mean_proof_review_completed":mean["independent_mean_math_review"]["status"]=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN",
             "mathematical_mean_support_review_status":mean["independent_mean_math_review"]["status"],
             "independent_mean_math_review":mean["independent_mean_math_review"],
             "artifact_sha256":core.artifact_hashes(out,result["case"]),
             "elapsed_wall_seconds":time.perf_counter()-started}
    core.atomic_text(out/"STDLIB_VERIFICATION_RECEIPT.json",json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt),flush=True)

if __name__=="__main__":main()
