"""Protocol-bound D2-a actual-direction uniform certificate adapter.

Reuse the unmodified R1 degree-8/Abel implementation in an isolated process.
New outputs are under work/d2a_cert_*. Point means use their own equilibrium
identity and the inherited deterministic mean tube, not an averaging identity.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import inspect
import sys
import threading
import time
sys.dont_write_bytecode = True
from d2a_core import calendar, normalize_raw, B, RATE, ETA, sqrt_upper

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "work/r1_extract/CERTO_FDI_STAGE_D1_ACTUAL_DIRECTION_20260919"
if sys.platform == "win32":
    SOURCE=Path(chr(92)*2+"?"+chr(92)+str(SOURCE.resolve()))
PROTOCOL_PATH=ROOT/"work/d2a_PROTOCOL_v1.json"
PROTOCOL_SHA=hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
assert PROTOCOL_SHA==(ROOT/"work/d2a_PROTOCOL_v1.sha256").read_text().strip()
PROTOCOL=json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
sys.path.insert(0,str(SOURCE/"src"))
import stage_context as sc
from event_accounting import budget
import risk_and_control as original_risk
sys.path.insert(0,str(SOURCE/"frozen"))

def serial(value):
    if isinstance(value,F):return str(value)
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    return value

def up(value,digits=22):
    value=F(value);scale=10**digits
    return F(-((-value.numerator*scale)//value.denominator),scale)

def read_json(path):return json.loads(path.read_text(encoding="utf-8"))

def atomic_text(path,text):
    temporary=path.with_name(path.name+".next")
    # Commit the exact bytes used for transaction hashes; Windows write_text's
    # newline translation must not turn a planned LF hash into CRLF payload.
    temporary.write_bytes(text.encode("utf-8"))
    deadline=time.monotonic()+20
    while True:
        try:
            os.replace(temporary,path)
            break
        except PermissionError as error:
            if os.name!="nt" or getattr(error,"winerror",None) not in (5,32,33) or time.monotonic()>=deadline:raise
            time.sleep(.05)

def review_binding(item):
    path=ROOT/"work/d2a_cert_mean_review_binding.json"
    if not path.exists():return {"status":"PENDING_SHARED_MEAN_REVIEW"}
    binding=read_json(path)
    assert binding["protocol_sha256"]==PROTOCOL_SHA
    report=ROOT/binding["report_path"]
    assert hashlib.sha256(report.read_bytes()).hexdigest()==binding["report_sha256"]
    assert _MEAN_SOURCE_DIGEST==binding["mean_function_after_scope_binding_sha256"]
    assert item["H_post_slots"]<=600 and item["T_fast_steps"]<=151000
    actual_max=F(3,10000)*F(item["H_post_slots"],4)
    assert actual_max<=F(9,200)
    return {**binding,"actual_case_fault_max":str(actual_max),
            "scope":"H0 f=0; H1 frozen 0.0003*(t-1)+ template, H<=600, actual f<=0.045; original beta box/rate; inherited nonlinear/event/contraction assumptions",
            "general_wide_f_0_75_mirror_coverage_claimed":False}

def guarded_mills(value):
    value=F(value)
    if value<=0:return F(1)
    floored=F(value.numerator*10**8//value.denominator,10**8)
    if floored<=0:return F(1)
    return original_risk.mills(floored)

def guarded_risk(m0,m1,b0,b1,vlo,vhi,event):
    z=F(25,8);sd=sc.dc.sq_up(vhi);threshold=m0+b0+z*sd;gap=m1-b1-threshold
    use=vhi if gap>=0 else vlo
    standardized=gap/sc.dc.sq_up(use) if gap>=0 else gap/sc.dc.sq_lo(use)
    if standardized>=0:
        power=max(F(0),1-guarded_mills(standardized)-event)
        miss=min(F(1),guarded_mills(standardized)+event)
    else:
        power,miss=F(0),F(1)
    return {"mean_H0_upper":m0,"mean_H1_lower":m1,"error_support_H0":b0,"error_support_H1":b1,
            "variance_lower":vlo,"variance_upper":vhi,"sd_upper":sd,"event_failure_per_hypothesis":event,
            "threshold_z":z,"threshold":threshold,"gap_lower":gap,
            "gap_sign_variance_choice":"upper" if gap>=0 else "lower","standardized_gap_lower":standardized,
            "false_alarm_upper":guarded_mills(z)+event,"miss_upper":miss,"power_lower":power,
            "target_pass":power>=F(9,10) and guarded_mills(z)+event<F(1,1000)}

def target_classification(covariance,risk):
    failures=[]
    if F(covariance["variance_ratio_upper"])>F(101,100):failures.append("VARIANCE_RATIO_TARGET_NOT_MET")
    target=F(risk["power_lower"])>=F(9,10) and F(risk["false_alarm_upper"])<F(1,1000)
    assert bool(risk["target_pass"])==target
    if not target:failures.append("RISK_TARGET_NOT_MET")
    return ("CERTIFIED_TARGET_PASS" if not failures else "VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET"),failures

def artifact_hashes(out,case):
    paths=[out/name for name in ("ACTUAL_PROTOCOL.json","PROJECTION_CERTIFICATE.json","DIRECTION.json")]
    paths += [out/"audit"/(case+suffix) for suffix in ("_DIRECTION_CERTIFICATE.json","_ADJOINT_JET.json.gz")]
    result={}
    for path in paths:
        with path.open("rb") as stream: digest=hashlib.file_digest(stream,"sha256").hexdigest()
        result[str(path.relative_to(out))]={"sha256":digest,"bytes":path.stat().st_size}
    return result

def design(item,readout):
    from projection import solve,rational_certificate
    obs=item["observations"];nodes=[o["relative_node"] for o in obs]
    tasks=[o["task"] for o in obs]
    target=[F(0) if j<=0 else e*ETA*(j-(F(1,2) if readout=="average250" else 0)) for j,e in zip(nodes,tasks)]
    _,edge,pin,iterations=solve(list(map(float,target)),nodes,float(B),float(RATE))
    certificate=rational_certificate(target,nodes,B,RATE,edge,pin)
    raw=[y-F(z) for y,z in zip(target,certificate["z"])]
    result=normalize_raw(raw,tasks)
    if result is None:return None,certificate
    result["iterations"]=iterations
    result["dual_support"]=sum((abs(F(q))*RATE*(nodes[i+1]-nodes[i]) for i,q in enumerate(certificate["q"])),F(0))+B*sum((abs(F(e)) for e in certificate["eta"]),F(0))
    assert result["dual_support"]==sum((a*F(z) for a,z in zip(raw,certificate["z"])),F(0))
    assert sum((a*y for a,y in zip(raw,target)),F(0))-result["dual_support"]==result["raw_norm_squared"]
    return result,certificate

def actual_protocol(item,readout,direction):
    weights=[]
    for o,value in zip(item["observations"],direction["physical"]):
        if not value:continue
        start,stop=(o["average_indices"] if readout=="average250" else (o["point_index"],o["point_index"]+1))
        weights.append({"start":start,"stop":stop,"value":str(value/(250 if readout=="average250" else 1))})
    denominator=math.lcm(*(F(s["value"]).denominator for s in weights))
    return {"T_fast_steps":item["T_fast_steps"],"move_intervals":item["moves"],
            "weight_denominator":denominator,"weights":weights,
            "protocol_sha256":PROTOCOL_SHA,"readout":readout,"calendar":item,
            "fault_onset_s":"1","fault_slope":"3/10000"}

def bind_actual(pr,out,case):
    spec=importlib.util.spec_from_file_location("d2a_original_actual_direction",SOURCE/"src/actual_direction.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=out;module.PROTOCOL=pr;module.CASE=case;module.T=pr["T_fast_steps"]
    module.MOVES=pr["move_intervals"];module.WDEN=pr["weight_denominator"]
    module.WS=math.lcm(10**24,module.WDEN)
    module.MOVING=[False]*module.T
    for start,stop in module.MOVES:module.MOVING[start:stop]=[True]*(stop-start)
    assert module.WS%module.WDEN==0
    return module

def mean_certificate(item,readout,direction):
    """Uniform deterministic path support relative to exact sampled ramp.

    Point: equilibrium L_beta q*=-d gives C X*=d4+beta Kp4 q*.
    Mean tube controls X^g-X*, including full carried entry mean. H0/H1
    have independent nuisance paths; each pays this same valid worst-case tube.
    """
    reviewed=review_binding(item)
    old=read_json(sc.RISK/"audit/DIRECTIONAL_RISK_CERTIFICATE.json")
    gp=max(abs(F(x)) for x in old["mean_load_coefficient_interval"])
    true_B=2*gp*F(1,50);true_rate=2*gp*F(1,1000)*F(1,4)
    gamma=max(true_B/B,true_rate/RATE)
    health=(gamma*direction["dual_support"]+true_B*direction["rounding_l1"])/(2*direction["normalizer"])
    assert health>=0
    sampled_times=[F(o["sample_average_time_s"] if readout=="average250" else o["point_sample_time_s"]) for o in item["observations"]]
    # Uniform sampling offsets are common, so real time gaps equal delta*node gaps.
    assert all(sampled_times[i+1]-sampled_times[i]==F(item["observations"][i+1]["relative_node"]-item["observations"][i]["relative_node"],4) for i in range(len(sampled_times)-1))
    weights=direction["physical"]
    signal=F(3,10000)*sum((w*max(F(0),t-1) for w,t in zip(weights,sampled_times)),F(0))
    mean_loss=F(0);details=[]
    if readout=="average250":
        for is_source in (True,False):
            rows=[(o,w) for o,w in zip(item["observations"],weights) if w and o["source_segment"]==is_source]
            if not rows:continue
            age=min(o["hold_start_age_steps"] for o,w in rows)
            inherited=original_risk.mean_dynamic_per_slot(is_source,age)
            # The original momentum/gradient identity uses continuous slot
            # averages. Exact discrete-ramp reference differs by kappa*h/2.
            radius=up(inherited["single_slot_dynamic_mean_error"]+F(3,20000000))
            l1=sum((abs(w) for o,w in rows),F(0))
            mean_loss+=l1*radius
            details.append({"source":is_source,"earliest_age_steps":age,"l1":l1,
                            "mean_per_read_radius":radius,"continuous_to_sampled_ramp_allowance":F(3,20000000),
                            "method":"inherited average momentum/gradient support plus sampled-ramp centering allowance"})
    else:
        admission=read_json(sc.RISK/"input/CERTO_FDI_STAGE_D1_NONLINEAR_ADMISSION_20260919/audit/ADMISSION_CERTIFICATE.json")
        hold=read_json(sc.PRE/"audit/FROZEN_HOLD_CERTIFICATE.json")
        metric=read_json(sc.PRE/"audit/DECAY_RATE_REFINED.json")
        P=sc.dc.fmat(next(x for x in metric["candidates"] if x["rho"]=="197/200")["P"])
        inverse,_=sc.im.inverse([[sc.I(x) for x in row] for row in P])
        pdiag=[F(inverse[i][i].hi,sc.im.S) for i in range(18)]
        equilibrium=[F(x) for x in hold["affine_equilibrium_radii"]]
        rate_tube=[F(x) for x in admission["rate_only_bound"]]
        geometry=read_json(sc.BASE/"audit/TANGENT_LIFTS.json")["geometry"]
        Kpabs=[[max(abs(F(a)),abs(F(b))) for a,b in row] for row in geometry["Kp"]]
        model=read_json(sc.D1C/"audit/PARAMETRIC_MODEL.json")
        Cabs=[max(abs(F(a)),abs(F(b))) for a,b in model["C"][0]]
        equilibrium_output_defect=up(F(1,50)*sum((k*x for k,x in zip(Kpabs[3],equilibrium)),F(0)))
        for is_source in (True,False):
            rows=[(o,w) for o,w in zip(item["observations"],weights) if w and o["source_segment"]==is_source]
            if not rows:continue
            age=min(o["point_hold_age_steps"] for o,w in rows)
            initial=[40*x for x in equilibrium]+[F(0)]*12
            if not is_source:
                initial=[x+F(y) for x,y in zip(initial,admission["entry"]["mean_radius"])]
                assert age>=1500
            metric_norm=sqrt_upper(sum((initial[i]*abs(P[i][j])*initial[j] for i in range(18) for j in range(18)),F(0)))
            rho=F(197,200)
            hom=[up(sqrt_upper(diag)*metric_norm*rho**age) for diag in pdiag]
            state_tube=[up(r+h) for r,h in zip(rate_tube,hom)]
            output_tube=up(sum((c*x for c,x in zip(Cabs,state_tube)),F(0)))
            radius=equilibrium_output_defect+output_tube
            l1=sum((abs(w) for o,w in rows),F(0));mean_loss+=l1*radius
            details.append({"source":is_source,"earliest_age_steps":age,"l1":l1,
                            "mean_per_read_radius":radius,"equilibrium_output_defect":equilibrium_output_defect,
                            "prestep_output_mean_tube":output_tube,"state_mean_about_equilibrium_tube":state_tube,
                            "initial_mean_radius":initial,"metric_homogeneous_radius":hom,
                            "method":"prestep C row + affine equilibrium identity + inherited rate/entry mean tube; no average identity"})
    eps=PROTOCOL["error_radii"]
    error=sum((abs(w)*F(eps[("average" if readout=="average250" else "point")+("_source" if o["source_segment"] else "_postmove")]) for o,w in zip(item["observations"],weights)),F(0))
    mu0=up(health+mean_loss);mu1=signal-up(health+mean_loss)
    return {"scope":"each full deterministic beta path; H0 f=0, H1 frozen ramp; independent nuisance choices; inherited comparison/event assumptions",
            "uniformity_source":"inherited equilibrium, rate-only/entry mean tubes and rho-P contraction; new output/support algebra",
            "health_support_per_hypothesis":up(health),"mean_dynamic_loss_per_hypothesis":up(mean_loss),
            "fault_signal_for_exact_sampled_times":signal,"mean_H0_upper":mu0,"mean_H1_lower":mu1,
            "error_H0":error,"error_H1":error,"mean_details":details,
            "health_dual_scale_factor":gamma,"actual_difference_box":true_B,"actual_difference_rate_per_slot":true_rate,
            "projection_rounding_support_allowance":true_B*direction["rounding_l1"]/(2*direction["normalizer"]),
            "two_hypothesis_budgets_paid":True,"point_uses_average_cancellation":False,
            "independent_mean_math_review":reviewed}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--H",type=int,default=120)
    parser.add_argument("--family",default="terminal_balanced")
    parser.add_argument("--stage-endpoint",type=int)
    parser.add_argument("--readout",choices=list(PROTOCOL["readouts"]),required=True)
    parser.add_argument("--verify-only",action="store_true")
    parser.add_argument("--derive-from-witness",action="store_true")
    args=parser.parse_args();started=time.perf_counter()
    suffix=(f"_S{args.stage_endpoint}" if args.stage_endpoint is not None else "")
    case=f"D2A_H{args.H}_{args.family}{suffix}_{args.readout}".upper()
    out=ROOT/f"work/d2a_cert_h{args.H}_{args.family}{suffix}_{args.readout}"
    out.mkdir(parents=True,exist_ok=True);(out/"audit").mkdir(exist_ok=True)
    checkpoint=ROOT/"work/d2a_cert_checkpoint.json"
    checkpoint_lock=threading.Lock()
    def phase(name,**extra):
        data={"case":case,"output_directory":str(out),"protocol_sha256":PROTOCOL_SHA,
              "phase":name,"elapsed_wall_seconds":time.perf_counter()-started,
              "command":f"python -B -X utf8 work/d2a_cert_case.py --H {args.H} --family {args.family} --readout {args.readout}",**extra}
        with checkpoint_lock:
            atomic_text(checkpoint,json.dumps(data,ensure_ascii=False,indent=2)+"\n")
        print("PHASE",name,flush=True)
    finished=threading.Event()
    main_thread=threading.get_ident()
    def heartbeat():
        while not finished.wait(30):
            frame=sys._current_frames().get(main_thread);observed={}
            while frame is not None:
                if frame.f_code.co_filename.endswith("actual_direction.py"):
                    observed={"function":frame.f_code.co_name,
                              **{key:frame.f_locals[key] for key in ("n","degree","T") if isinstance(frame.f_locals.get(key),int)}}
                    if observed.get("function")=="proposal" and "n" in observed:
                        observed["backward_fast_steps_generated"]=item["T_fast_steps"]-1-observed["n"]
                    break
                frame=frame.f_back
            with checkpoint_lock:
                if checkpoint.exists():
                    state=read_json(checkpoint)
                    state.update(elapsed_wall_seconds=time.perf_counter()-started,observed_progress=observed)
                    atomic_text(checkpoint,json.dumps(state,ensure_ascii=False,indent=2)+"\n")
                    print("HEARTBEAT",state["phase"],json.dumps(observed),flush=True)
    phase("DESIGN_AND_CONTRACT")
    item=calendar(args.H,args.family,args.stage_endpoint)
    assert not item["validation_errors"]
    direction,projection=design(item,args.readout)
    if direction is None:
        (out/"CASE_RESULT.json").write_text(json.dumps({"status":"ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE","calendar":item,"protocol_sha256":PROTOCOL_SHA},indent=2)+"\n")
        phase("COMPLETE_ZERO_DIRECTION")
        return
    pr=actual_protocol(item,args.readout,direction)
    (out/"ACTUAL_PROTOCOL.json").write_text(json.dumps(pr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"PROJECTION_CERTIFICATE.json").write_text(json.dumps(projection,indent=2)+"\n",encoding="utf-8")
    (out/"DIRECTION.json").write_text(json.dumps(serial(direction),indent=2)+"\n",encoding="utf-8")
    adapter=bind_actual(pr,out,case)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    if not args.verify_only and not args.derive_from_witness:
        phase("GENERATE_DEGREE8_ADJOINT_WITNESS",T=adapter.T,WS=str(adapter.WS),WDEN=str(adapter.WDEN))
        adapter.proposal()
        phase("CERTIFY_RECURSIONS_ABEl_AND_SUPERSOLUTIONS")
        covariance=adapter.certify(False)
    elif args.derive_from_witness:
        phase("DERIVE_CERTIFICATE_FROM_SAVED_WITNESS")
        covariance=adapter.certify(False)
    else:
        phase("RECERTIFY_FROM_SAVED_WITNESS")
        covariance=adapter.certify(True)
    phase("UNIFORM_MEAN_AND_EVENT_RISK")
    mean=mean_certificate(item,args.readout,direction)
    events=budget(item["T_fast_steps"],len(item["moves"]))
    risk=guarded_risk(mean["mean_H0_upper"],mean["mean_H1_lower"],mean["error_H0"],mean["error_H1"],
                            covariance["variance_lower"],covariance["variance_upper"],events["total_failure"])
    arithmetic_status,failure=target_classification(covariance,risk)
    reviewed=mean["independent_mean_math_review"]
    accepted_math=reviewed["status"]=="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN"
    result={"case":case,"protocol_sha256":PROTOCOL_SHA,"calendar":item,"readout":args.readout,
            "status":arithmetic_status if accepted_math else "PENDING_SHARED_MEAN_REVIEW", "arithmetic_risk_target_status":arithmetic_status,
            "shared_mean_review_status":reviewed["status"],"independent_mean_math_review":reviewed,
            "failure_classification":failure,"uniform_mean":mean,"uniform_variance":covariance,
            "event_accounting":events,"protected_risk":risk,"elapsed_wall_seconds":time.perf_counter()-started,
            "original_scientific_source_modified":False,"new_point_mean_algebra_requires_independent_review":not accepted_math}
    (out/"CASE_RESULT.json").write_text(json.dumps(serial(result),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"case":case,"status":result["status"],"arithmetic_risk_target_status":arithmetic_status,"failure":failure,
             "variance_lower":float(covariance["variance_lower"]),"variance_upper":float(covariance["variance_upper"]),
             "variance_ratio_upper":float(covariance["variance_ratio_upper"]),
             "mean_H0_upper":float(mean["mean_H0_upper"]),"mean_H1_lower":float(mean["mean_H1_lower"]),
             "dynamic_loss":float(mean["mean_dynamic_loss_per_hypothesis"]),"error_per_side":float(mean["error_H0"]),
             "gap":float(risk["gap_lower"]),"power_lower":float(risk["power_lower"]),
             "false_alarm_upper":float(risk["false_alarm_upper"]),"event":float(events["total_failure"]),
             "elapsed_wall_seconds":result["elapsed_wall_seconds"]}
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    phase("COMPLETE",summary=summary)
    finished.set()
    print(json.dumps(summary,ensure_ascii=False),flush=True)

_MEAN_SOURCE_DIGEST=hashlib.sha256(inspect.getsource(mean_certificate).encode("utf-8")).hexdigest()

if __name__=="__main__":
    try:
        main()
    except Exception as error:
        import traceback
        checkpoint=ROOT/"work/d2a_cert_checkpoint.json"
        previous=read_json(checkpoint) if checkpoint.exists() else {}
        failure={**previous,"phase":"FAILED","failure_type":type(error).__name__,
                 "failure_message":str(error),"traceback":traceback.format_exc()}
        atomic_text(checkpoint,json.dumps(failure,ensure_ascii=False,indent=2)+"\n")
        if previous.get("output_directory"):
            (Path(previous["output_directory"])/"FAILED_CASE.json").write_text(json.dumps(failure,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        traceback.print_exc()
        sys.exit(1)
