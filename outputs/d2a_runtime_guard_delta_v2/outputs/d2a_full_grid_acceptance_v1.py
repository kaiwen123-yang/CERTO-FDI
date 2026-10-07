"""Read-only metadata acceptance for the frozen D2-a grid.
No imports from scientific runners, no subprocess, no witness reads, no writes.
Exit: 0 full metadata accepted; 2 valid but incomplete/stale; 3 invalid;
4 explicit unresolved classified failures. Scientific byte/ZIP acceptance separate.
"""
from pathlib import Path
from fractions import Fraction as F
import argparse, ast, collections, csv, hashlib, io, json, re, sys
if hasattr(sys, "set_int_max_str_digits"): sys.set_int_max_str_digits(0)
PROTOCOL_SHA = "0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6"
GRID = (40,60,80,100,120,160,200,240,300,400,500,600)
FAMILIES = ("stay","fixed20","fixed40","fixed76","terminal_balanced","switch_then_stay")
READOUTS = ("average250","point_last_fast_read")
VALID = {"CERTIFIED_TARGET_PASS","VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET"}
ZERO = "ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"
PENDING = {"NOT_RUN","PENDING_SHARED_MEAN_REVIEW"}
FAILURES = {"CERTIFICATION_EXECUTION_FAILED","PHYSICAL_CONTRACT_FAILED",
            "PROJECTION_CERTIFICATE_FAILED","MEAN_CERTIFICATE_MISSING_OR_FAILED",
            "VARIANCE_CERTIFICATE_MISSING_OR_FAILED","DIRECTION_OR_CONTRACT_FAILURE"}
DONE = VALID | {ZERO}
HEX = re.compile(r"^[0-9a-f]{64}$")

def key(row):
    endpoint=row.get("stage_endpoint")
    return (int(row["H_post_slots"]),row["family"],
            None if endpoint in (None,"") else int(endpoint),row["readout"])

def expected_keys(grid=GRID, families=FAMILIES, readouts=READOUTS):
    return [(h,f,s,r) for h in grid for f in families
            for s in (range(20,h+1,20) if f=="switch_then_stay" else [None])
            for r in readouts]

def coverage(rows, expected):
    counts=collections.Counter(key(r) for r in rows)
    exp=set(expected)
    return {"missing":sorted(exp-set(counts),key=str),
            "unexpected":sorted(set(counts)-exp,key=str),
            "duplicates":[(k,n) for k,n in counts.items() if n>1]}

def selections(rows, expected, grid=GRID, families=FAMILIES, readouts=READOUTS):
    by={key(r):r for r in rows}
    answers=[]
    for r in readouts:
        for f in families:
            answer={"readout":r,"family":f,"first_success_H":None,"all_grid_complete":True}
            prior=True
            for h in grid:
                ks=[k for k in expected if k[0]==h and k[1]==f and k[3]==r]
                closed=bool(ks) and all(k in by and by[k]["risk_status"] in DONE for k in ks)
                answer["all_grid_complete"] &= closed
                passed=[by[k] for k in ks if k in by and by[k]["risk_status"]=="CERTIFIED_TARGET_PASS"]
                if answer["first_success_H"] is None and prior and closed and passed:
                    winner=min(passed,key=lambda q:(-F(q["protected_power_lower"]),key(q)[2] or 0))
                    answer.update(first_success_H=h,physical_endpoint_seconds=str(F(h+4,4)),
                                  selected_stage_endpoint=key(winner)[2],
                                  predecessor_and_current_members_closed=True)
                prior &= closed
            answers.append(answer)
    return answers

def risk_checks(row):
    names=("Vminus","Vplus","variance_ratio_upper","mu0_upper","mu1_lower",
           "b0","b1","threshold","gap","false_alarm_upper","protected_power_lower",
           "event_budget_per_hypothesis")
    v={}
    for n in names:
        x=row.get(n)
        if x in (None,"","NA"): raise ValueError("missing numeric "+n)
        v[n]=F(x)
    if not (0<=v["Vminus"]<=v["Vplus"] and v["Vplus"]>0):raise ValueError("invalid variance interval")
    if not (0<=v["protected_power_lower"]<=1 and 0<=v["false_alarm_upper"]<=1):raise ValueError("risk not probability")
    if min(v["b0"],v["b1"],v["event_budget_per_hypothesis"])<0:raise ValueError("negative allowance")
    if v["gap"]!=v["mu1_lower"]-v["b1"]-v["threshold"]:raise ValueError("gap identity")
    if v["gap"]<=0 and v["protected_power_lower"]!=0:raise ValueError("nonpositive gap with positive power")
    margin=v["threshold"]-v["mu0_upper"]-v["b0"]
    if margin<0 or margin**2<F(25,8)**2*v["Vplus"]:raise ValueError("null threshold margin")
    passed=(v["variance_ratio_upper"]<=F(101,100) and v["false_alarm_upper"]<F(1,1000)
            and v["protected_power_lower"]>=F(9,10))
    if passed!=(row["risk_status"]=="CERTIFIED_TARGET_PASS"):raise ValueError("status/numeric contradiction")
    return v

def signature(record):
    c=record["calendar"]
    obj={n:record[n] for n in ("protocol_sha256","readout","direction")}
    obj.update(T_fast_steps=c["T_fast_steps"],moves=c["moves"],observations=c["observations"])
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def terminal(h,proto):
    k=proto["k_slots"];xi=F(proto["terminal_balanced"]["xi_exact"])
    ns=[];used=0;l=1
    while True:
        x=xi*l/2;n=2*(-((-x.numerator)//x.denominator))
        if used+2*(n+k)>h:break
        ns.append(n);used+=2*(n+k);l+=1
    if ns:
        q,rem=divmod((h-used)//4,len(ns))
        ns=[n+2*q+2*(i<rem) for i,n in enumerate(ns)]
    obs=[];off=0
    for n in ns:
        half=n//2
        obs.extend((off+j,1) for j in range(1,half+1))
        obs.extend((off+j,-1) for j in range(half+k+1,3*half+k+1))
        obs.extend((off+j,1) for j in range(3*half+2*k+1,2*(n+k)+1))
        off+=2*(n+k)
    obs.extend((j,1) for j in range(off+1,h+1))
    return obs,len(ns)

def expected_calendar(h,f,s,proto):
    k=proto["k_slots"]
    if f=="stay":return [(j,1) for j in range(1,h+1)],0
    if f.startswith("fixed"):
        n=int(f[5:]);obs=[];at=0;task=1
        while at<h:
            count=min(n,h-at);obs.extend((j,task) for j in range(at+1,at+count+1));at+=count
            if h-at<=k:
                obs.extend((j,task) for j in range(at+1,h+1));break
            at+=k;task=-task
        return obs,0
    stage=h if f=="terminal_balanced" else s
    obs,b=terminal(stage,proto)
    obs.extend((j,1) for j in range(stage+1,h+1))
    return obs,b

class SmallReader:
    def __init__(self,root):self.root=root.resolve();self.cache={};self.total=0
    def path(self,value):
        p=(self.root/str(value).replace("\\","/")).resolve()
        if not p.is_relative_to(self.root):raise ValueError("outside workspace "+str(value))
        return p
    def raw(self,value,expected_hash=None):
        p=self.path(value)
        if p.suffix not in (".json",".md"):raise ValueError("not permitted small metadata type "+str(value))
        if p not in self.cache:
            n=p.stat().st_size
            if n>2*1024**2:raise ValueError("not small metadata "+str(value))
            self.total+=n
            if self.total>256*1024**2:raise ValueError("small metadata total cap")
            self.cache[p]=p.read_bytes()
        b=self.cache[p]
        if expected_hash is not None and hashlib.sha256(b).hexdigest()!=expected_hash:
            raise ValueError("bound small file hash changed "+str(value))
        return b
    def obj(self,value,expected_hash=None):return json.loads(self.raw(value,expected_hash).decode("utf-8-sig"))

def check_calendar(record,row,proto):
    h,f,s,r=key(row);c=record["calendar"];obs=c["observations"]
    expected,b=expected_calendar(h,f,s,proto)
    actual=[(o["relative_node"],o["task"]) for o in obs]
    if actual!=[(j,1) for j in range(-3,1)]+expected:raise ValueError("calendar/rounding mismatch")
    if c["H_post_slots"]!=h or record["readout"]!=r:raise ValueError("record identity")
    if c["T_fast_steps"]!=250*(h+4) or F(row["elapsed_seconds"])!=F(h+4,4):raise ValueError("time budget")
    if int(row["completed_symmetric_blocks"])!=b or c["completed_symmetric_blocks"]!=b:raise ValueError("block count")
    if c.get("validation_errors") or c.get("physical_contract_validated") is not True:raise ValueError("physical failed")
    moves=c["moves"]
    if int(row["transfers"])!=len(moves):raise ValueError("move count")
    for i,(a,z) in enumerate(moves):
        if z-a!=1500 or (a if i==0 else a-moves[i-1][1])<1750:raise ValueError("move/return clock")
    for o in obs:
        j=o["slot_zero_based"];start=250*j;stop=250*(j+1)
        arrivals=[z for a,z in moves if z<=start];arrival=arrivals[-1] if arrivals else 0
        if o["relative_node"]!=j-3 or o["average_indices"]!=[start,stop] or o["point_index"]!=stop-1:
            raise ValueError("sample indices")
        if F(o["available_time_s"])!=F(stop,1000) or F(o["point_sample_time_s"])!=F(stop-1,1000):
            raise ValueError("sample/availability time")
        if F(o["sample_average_time_s"])!=F(2*start+249,2000):raise ValueError("average sampled center")
        if o["source_segment"]!=(not arrivals) or o["hold_start_age_steps"]!=start-arrival:
            raise ValueError("source/post classification")
        if arrivals and start-arrival<1500:raise ValueError("read before settle")
    direction=record["direction"]
    if direction is not None:
        physical=list(map(F,direction["physical"]))
        if len(physical)!=len(obs) or not any(physical):raise ValueError("direction shape")
        raw=list(map(F,direction["raw"]));rounded=list(map(F,direction["rounded"]))
        if bool(direction["exact_zero_moment_preserved"])!=(sum(raw)==0):raise ValueError("raw moment rule")
        if sum(raw)==0 and sum(rounded)!=0:raise ValueError("zero moment not preserved")
        norm=sum((x*x for x in physical),F(0))
        if not 0<norm<=1 or norm!=F(direction["direction_norm_squared"]):raise ValueError("direction norm")
    return b

def check_completed(row,record,reader,proto,mean_binding):
    num=risk_checks(row)
    if row["physical_rule_status"]!="PASS_INHERITED_RULE_INSTANCE_CHECK":raise ValueError("physical status")
    for n in ("case_result_sha256","current_receipt_sha256","witness_sha256","covariance_certificate_sha256"):
        if not HEX.fullmatch(row.get(n,"")):raise ValueError("missing hash "+n)
    ref=row["certificate_reference"];case=reader.obj(ref+"/CASE_RESULT.json",row["case_result_sha256"])
    receipt=reader.obj(row["current_receipt_path"],row["current_receipt_sha256"])
    if receipt["status"] not in ("PASS_STDLIB_NEW_CASE_VERIFIER","PASS_STDLIB_DERIVED_REBINDING"):raise ValueError("receipt not pass")
    if receipt.get("numpy_loaded") is not False or receipt.get("scipy_loaded") is not False:
        raise ValueError("receipt not independent stdlib scope")
    if receipt["status"]=="PASS_STDLIB_NEW_CASE_VERIFIER":
        flags=("projection_KKT_exact","actual_protocol_exact","integer_interval_recursions_rechecked",
               "Abel_and_supersolutions_rechecked","uniform_mean_event_risk_recomputed")
        if any(receipt.get(x) is not True for x in flags):raise ValueError("full receipt missing scientific gates")
    elif not receipt.get("exact_KKT_protocol_direction_rechecked") or not receipt.get("mean_event_risk_recomputed"):
        raise ValueError("derived receipt missing small recomputation gates")
    if receipt["protocol_sha256"]!=PROTOCOL_SHA or case["protocol_sha256"]!=PROTOCOL_SHA:raise ValueError("case protocol")
    if receipt["case_result_sha256"]!=row["case_result_sha256"]:raise ValueError("receipt case binding")
    if case.get("arithmetic_risk_target_status",case["status"])!=row["risk_status"]:
        raise ValueError("table/case target classification")
    if ";".join(case["failure_classification"])!=row.get("failure_classification",""):
        raise ValueError("table/case failure classification")
    covariance_path=ref+"/audit/"+case["case"]+"_DIRECTION_CERTIFICATE.json"
    actual_covariance=reader.obj(covariance_path,row["covariance_certificate_sha256"])
    if actual_covariance!=case["uniform_variance"]:raise ValueError("case/covariance payload")
    if case["readout"]!=record["readout"]:raise ValueError("alias readout changed")
    direction=reader.obj(ref+"/DIRECTION.json")
    if signature({"protocol_sha256":case["protocol_sha256"],"calendar":case["calendar"],
                  "readout":case["readout"],"direction":direction})!=signature(record):raise ValueError("alias semantic mismatch")
    if case.get("shared_mean_review_status")!="ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN":raise ValueError("mean review pending")
    if row["mean_review_report_sha256"]!=mean_binding["report_sha256"]:raise ValueError("old mean review")
    if case["independent_mean_math_review"]["report_sha256"]!=mean_binding["report_sha256"]:raise ValueError("case old mean")
    case_review=case["independent_mean_math_review"]
    if F(case_review["actual_case_fault_max"])!=F(3*int(row["H_post_slots"]),40000):
        raise ValueError("fault-template scope")
    if case_review.get("general_wide_f_0_75_mirror_coverage_claimed") is not False:
        raise ValueError("wide fault unsupported")
    mean=case["uniform_mean"];risk=case["protected_risk"];cov=case["uniform_variance"]
    if not mean.get("two_hypothesis_budgets_paid") or mean.get("point_uses_average_cancellation"):raise ValueError("two-sided/point mean")
    mapping={"mu0_upper":mean["mean_H0_upper"],"mu1_lower":mean["mean_H1_lower"],
             "b0":mean["error_H0"],"b1":mean["error_H1"],"Vminus":cov["variance_lower"],
             "Vplus":cov["variance_upper"],"variance_ratio_upper":cov["variance_ratio_upper"],
             "threshold":risk["threshold"],"gap":risk["gap_lower"],
             "false_alarm_upper":risk["false_alarm_upper"],"protected_power_lower":risk["power_lower"],
             "event_budget_per_hypothesis":risk["event_failure_per_hypothesis"]}
    if any(num[n]!=F(x) for n,x in mapping.items()):raise ValueError("table/case numeric binding")
    if F(risk["error_support_H0"])!=num["b0"] or F(risk["error_support_H1"])!=num["b1"]:raise ValueError("side allowances")
    if risk["gap_sign_variance_choice"]!=("upper" if num["gap"]>=0 else "lower"):raise ValueError("gap variance sign")
    events=case["event_accounting"]
    if events["n_fast_steps"]!=case["calendar"]["T_fast_steps"] or events["transfers"]!=len(case["calendar"]["moves"]):
        raise ValueError("event clock")
    if F(events["total_failure"])!=num["event_budget_per_hypothesis"] or events.get("independence_used") is not False:
        raise ValueError("event/independence")
    if receipt["status"]=="PASS_STDLIB_DERIVED_REBINDING":
        if not receipt.get("uniform_variance_payload_unchanged") or receipt.get("big_adjoint_recursions_reexecuted"):
            raise ValueError("derived receipt scope")
        prior=reader.obj(receipt["prior_full_stdlib_receipt_path"],receipt["prior_full_stdlib_receipt_sha256"])
        old=reader.raw(receipt["prior_case_result_path"],receipt["prior_case_result_sha256"])
        if prior["case_result_sha256"]!=hashlib.sha256(old).hexdigest():raise ValueError("prior receipt chain")
        if prior["status"]!="PASS_STDLIB_NEW_CASE_VERIFIER" or prior["protocol_sha256"]!=PROTOCOL_SHA:
            raise ValueError("derived chain lacks original full verifier")
        prior_case=json.loads(old)
        if prior_case["uniform_variance"]!=cov or prior_case["readout"]!=case["readout"]:
            raise ValueError("derived variance/readout changed")
        if receipt["uniform_variance_payload_sha256"]!=row["covariance_certificate_sha256"]:
            raise ValueError("derived covariance byte binding changed")
    if row.get("evidence_hash_binding_status")!="BOUND_AT_VERIFICATION_OR_HASH_ONLY_RECEIPT":raise ValueError("artifacts unbound")
    artifacts=receipt.get("artifact_sha256")
    if receipt.get("artifact_sha256") is None:
        binding=reader.obj(row["evidence_hash_binding_path"],row["evidence_hash_binding_sha256"])
        if binding["case_result_sha256"]!=row["case_result_sha256"]:raise ValueError("sidecar case")
        selected={"path":Path(row["current_receipt_path"].replace("\\","/")).name,"sha256":row["current_receipt_sha256"]}
        if selected not in binding["verified_receipts"]:raise ValueError("sidecar selected receipt")
        artifacts=binding["artifact_sha256"]
    witnesses=[x["sha256"] for n,x in artifacts.items() if n.endswith("_ADJOINT_JET.json.gz")]
    covariances=[x["sha256"] for n,x in artifacts.items() if n.endswith("_DIRECTION_CERTIFICATE.json")]
    if witnesses!=[row["witness_sha256"]] or covariances!=[row["covariance_certificate_sha256"]]:
        raise ValueError("artifact hash binding/table mismatch")
    witness=reader.path(ref+"/audit/"+case["case"]+"_ADJOINT_JET.json.gz")
    if not witness.is_file():raise ValueError("bound witness absent (not opened)")
    return signature(record)

def run(root):
    root=root.resolve();reader=SmallReader(root)
    pb=reader.raw("work/d2a_PROTOCOL_v1.json",PROTOCOL_SHA);proto=json.loads(pb)
    if tuple(proto["H_post_slots"])!=GRID or tuple(proto["calendar_families"])!=FAMILIES:raise ValueError("frozen grid changed")
    table=(root/"work/d2a_cert_review_bound_table.csv").read_bytes()
    if len(table)>16*1024**2:raise ValueError("table size cap")
    table_hash=hashlib.sha256(table).hexdigest()
    receipt=reader.obj("work/d2a_cert_review_bound_table_receipt.json")
    if receipt["protocol_sha256"]!=PROTOCOL_SHA:raise ValueError("view protocol")
    if receipt["table_sha256"]!=table_hash:
        return {"status":"INCOMPLETE_CHANGING_VIEW","exit_code":2,"full_grid_accepted":False}
    rows=list(csv.DictReader(io.StringIO(table.decode("utf-8-sig"))))
    expected=expected_keys()
    bad=coverage(rows,expected)
    errors=[{"check":"coverage","details":bad}] if any(bad.values()) else []
    binding=reader.obj("work/d2a_cert_mean_review_binding.json")
    reader.raw(binding["report_path"],binding["report_sha256"])
    source=(root/"work/d2a_cert_case.py").read_text(encoding="utf-8")
    lines=source.splitlines(keepends=True)
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=="mean_certificate")
    digest=hashlib.sha256("".join(lines[fn.lineno-1:fn.end_lineno]).encode()).hexdigest()
    if digest!=binding["mean_function_after_scope_binding_sha256"]:raise ValueError("current mean function not review-bound")
    counts=collections.Counter(r["risk_status"] for r in rows)
    if dict(counts)!=receipt["status_counts"]:errors.append({"check":"receipt counts"})
    aliases=collections.defaultdict(list);blocks=collections.Counter();eligible=0
    for row in rows:
        try:
            status=row["risk_status"]
            if status not in DONE|PENDING|FAILURES:raise ValueError("unknown status "+status)
            record=reader.obj(row["direction_record_path"],row["direction_record_sha256"])
            if record["protocol_sha256"]!=PROTOCOL_SHA:raise ValueError("direction protocol")
            b=check_calendar(record,row,proto);blocks[(key(row)[0],key(row)[1],b)]+=1
            if row["family"] in ("terminal_balanced","switch_then_stay") and b>=3:eligible+=1
            if status==ZERO:
                if record["direction"] is not None:raise ValueError("zero status with nonzero direction")
                if any(row.get(n) not in (None,"","NA") for n in ("Vplus","false_alarm_upper","protected_power_lower")):
                    raise ValueError("zero direction has substituted risk numbers")
            elif status in VALID:
                if record["direction"] is None:raise ValueError("certificate with zero direction")
                sig=check_completed(row,record,reader,proto,binding)
                aliases[row["certificate_reference"]].append((key(row),sig))
            elif status in FAILURES and not row.get("failure_classification"):
                raise ValueError("failure not classified")
        except (KeyError,ValueError,AssertionError,OSError,json.JSONDecodeError) as err:
            errors.append({"row":list(key(row)),"error":str(err)})
    for ref,members in aliases.items():
        if len({sig for k,sig in members})!=1:errors.append({"check":"alias group","reference":ref})
    pending=sum(counts.get(x,0) for x in PENDING);failed=sum(counts.get(x,0) for x in FAILURES)
    status="FAIL_CLOSED_INVALID_METADATA" if errors else ("INCOMPLETE_VALID_METADATA" if pending
            else ("CLASSIFIED_FAILURES_REQUIRE_REVIEW" if failed else "PASS_FULL_GRID_METADATA"))
    code=3 if errors else 2 if pending else 4 if failed else 0
    return {"status":status,"exit_code":code,"full_grid_accepted":code==0,
            "scope":"Small metadata acceptance only; no scientific witness arithmetic/hash or final ZIP acceptance.",
            "protocol_sha256":PROTOCOL_SHA,"table_sha256":table_hash,"expected_rows":len(expected),"actual_rows":len(rows),
            "counts":dict(counts),"coverage_errors":bad,"errors":errors,"pending_rows":pending,
            "unaccepted_failure_rows":failed,"alias_groups_with_multiple_rows":sum(len(v)>1 for v in aliases.values()),
            "logical_rows_preserved":len(rows),"accepted_nonzero_unique_references":len(aliases),
            "original_three_block_reference_eligible_rows":eligible,
            "terminal_blocks_by_H":{str(h):b for h,f,b in blocks if f=="terminal_balanced"},
            "first_certified_grid":selections(rows,expected) if not errors else [],
            "small_metadata_bytes_read":reader.total,"large_witness_bytes_read":0}

def self_test():
    tests=[]
    expected=[(40,"switch_then_stay",20,"a"),(40,"switch_then_stay",40,"a"),
              (60,"switch_then_stay",20,"a"),(60,"switch_then_stay",40,"a"),(60,"switch_then_stay",60,"a")]
    def row(k,status,power=None):
        return dict(H_post_slots=k[0],family=k[1],stage_endpoint=k[2],readout=k[3],
                    risk_status=status,protected_power_lower=power)
    base=[row(k,ZERO) for k in expected]
    base[-2]=row(expected[-2],"CERTIFIED_TARGET_PASS","9/10")
    base[-1]=row(expected[-1],"CERTIFIED_TARGET_PASS","9/10")
    test=lambda name,ok:tests.append({"name":name,"pass":bool(ok)})
    test("complete repeated calendar labels retained",not any(coverage(base,expected).values()) and len(base)==5)
    answer=selections(base,expected,(40,60),("switch_then_stay",),("a",))[0]
    test("tie chooses smallest S among certified",answer["first_success_H"]==60 and answer["selected_stage_endpoint"]==40)
    missing=base[1:]
    test("missing predecessor cannot exploit all(empty)",bool(coverage(missing,expected)["missing"]) and
         selections(missing,expected,(40,60),("switch_then_stay",),("a",))[0]["first_success_H"] is None)
    duplicate=base[1:]+[base[-1].copy()]
    test("same row count does not excuse duplicate/missing key",len(duplicate)==len(base) and
         bool(coverage(duplicate,expected)["duplicates"]) and bool(coverage(duplicate,expected)["missing"]))
    incomplete=[x.copy() for x in base];incomplete[0]["risk_status"]="NOT_RUN"
    test("pending earlier member blocks first success",selections(incomplete,expected,(40,60),("switch_then_stay",),("a",))[0]["first_success_H"] is None)
    numbers=dict(Vminus="1/100000000",Vplus="1/100000000",variance_ratio_upper="1",
                 mu0_upper="0",mu1_lower="2",b0="0",b1="0",threshold="1",gap="1",
                 false_alarm_upper="1/2000",protected_power_lower="9/10",
                 event_budget_per_hypothesis="0",risk_status="CERTIFIED_TARGET_PASS")
    risk_checks(numbers);test("positive complete risk metadata accepted",True)
    def rejects(x):
        try:risk_checks(x);return False
        except ValueError:return True
    bad=numbers|{"mu1_lower":"0","gap":"-1"}
    test("negative gap fake positive power rejected",rejects(bad))
    test("missing power is not numeric zero",rejects(numbers|{"protected_power_lower":""}))
    test("PFA equality is not strict pass",rejects(numbers|{"false_alarm_upper":"1/1000"}))
    test("full original cardinality",len(expected_keys())==400 and len(set(expected_keys()))==400)
    identity={"protocol_sha256":PROTOCOL_SHA,"readout":"average250",
              "calendar":{"T_fast_steps":11000,"moves":[],"observations":[{"node":1}],
                          "family":"stay","stage_endpoint":None},
              "direction":{"physical":["1"]}}
    alias=json.loads(json.dumps(identity));alias["calendar"]["family"]="switch_then_stay"
    alias["calendar"]["stage_endpoint"]=20
    test("physical identity aliases ignore labels but preserve rows",signature(identity)==signature(alias))
    changed=json.loads(json.dumps(alias));changed["readout"]="point_last_fast_read"
    test("wrong readout is not an identity alias",signature(identity)!=signature(changed))
    reader=SmallReader(Path.cwd())
    try:reader.raw("work/not_opened_ADJOINT_JET.json.gz");blocked=False
    except ValueError:blocked=True
    test("scientific witness type blocked before read",blocked and reader.total==0)
    try:reader.path("../outside.json");outside=False
    except ValueError:outside=True
    test("outside-workspace receipt path rejected",outside)
    return {"status":"PASS_TINY_FAIL_CLOSED_FIXTURES" if all(x["pass"] for x in tests) else "FAIL_TINY_FIXTURES",
            "tests":tests,"science_or_big_witness_executed":False,"filesystem_writes":False}

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--self-test",action="store_true");a=p.parse_args()
    if a.self_test:
        out=self_test();code=0 if all(x["pass"] for x in out["tests"]) else 3
    else:
        try:out=run(a.root);code=out["exit_code"]
        except (OSError,ValueError,KeyError,json.JSONDecodeError) as err:
            out={"status":"FAIL_CLOSED_INVALID_INPUT","exit_code":3,"error":str(err),"full_grid_accepted":False};code=3
    print(json.dumps(out,ensure_ascii=False,indent=2));return code
if __name__=="__main__":raise SystemExit(main())
