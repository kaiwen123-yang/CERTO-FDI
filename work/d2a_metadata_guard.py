"""Pure stdlib metadata guards. No runner/science imports or filesystem writes."""
from fractions import Fraction as F
import collections, csv, hashlib, io, json
PROTOCOL_SHA="0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6"
KNOWN={"CERTIFIED_TARGET_PASS","VALID_UNIFORM_CERTIFICATE_TARGET_NOT_MET","ZERO_DIRECTION_NO_SEPARATION_CERTIFICATE"}
BINDING_FIELDS=("direction_record_sha256","case_result_sha256","current_receipt_path",
    "current_receipt_sha256","witness_sha256","covariance_certificate_sha256",
    "evidence_hash_binding_status","evidence_hash_binding_path","evidence_hash_binding_sha256",
    "mean_review_report_sha256","mean_review_scope")

class MetadataCoverageError(ValueError):pass
class PhysicalContractError(ValueError):pass

def row_key(row):
    try:
        s=row.get("stage_endpoint")
        return (int(row["H_post_slots"]),row["family"],None if s in (None,"") else int(s),row["readout"])
    except (KeyError,TypeError,ValueError) as e:
        raise MetadataCoverageError("Invalid row identity: "+str(e)) from e

def expected_keys(protocol):
    keys=[]
    for h in protocol["H_post_slots"]:
        for family in protocol["calendar_families"]:
            stages=range(20,h+1,20) if family=="switch_then_stay" else [None]
            for s in stages:
                for readout in protocol["readouts"]:keys.append((h,family,s,readout))
    return keys

def validate_keyset(rows,expected):
    counts=collections.Counter(row_key(r) for r in rows);wanted=set(expected)
    missing=sorted(wanted-set(counts),key=str);unexpected=sorted(set(counts)-wanted,key=str)
    duplicates=[(k,n) for k,n in counts.items() if n!=1]
    if missing or unexpected or duplicates or len(expected)!=len(wanted):
        raise MetadataCoverageError(json.dumps({"missing":missing,"unexpected":unexpected,"duplicates":duplicates}))
    return {row_key(r):r for r in rows}

def select_pairs(rows,protocol,expected):
    by=validate_keyset(rows,expected);answers=[];grid=protocol["H_post_slots"]
    for readout in protocol["readouts"]:
        for family in protocol["calendar_families"]:
            family_keys=[k for k in expected if k[1]==family and k[3]==readout]
            if not family_keys:raise MetadataCoverageError("Empty expected family")
            answer={"readout":readout,"family":family,"first_success_H":None,
                    "all_grid_complete":all(by[k]["risk_status"] in KNOWN for k in family_keys)}
            predecessors_complete=True
            for h in grid:
                current_keys=[k for k in family_keys if k[0]==h]
                if not current_keys:raise MetadataCoverageError("Empty expected H/family")
                completed=all(by[k]["risk_status"] in KNOWN for k in current_keys)
                passing=[by[k] for k in current_keys if by[k]["risk_status"]=="CERTIFIED_TARGET_PASS"]
                if passing and predecessors_complete and completed:
                    try:selected=min(passing,key=lambda r:(-F(r["protected_power_lower"]),row_key(r)[2] or 0))
                    except (KeyError,TypeError,ValueError,ZeroDivisionError) as e:
                        raise MetadataCoverageError("Missing/invalid certified power: "+str(e)) from e
                    answer.update(first_success_H=h,physical_endpoint_seconds=str(F(h+4,4)),
                                  predecessor_grid_rows_complete=True,family_selection_at_H_complete=True,
                                  selected_stage_endpoint=selected["stage_endpoint"] or None,
                                  selected_certificate=selected["certificate_reference"],
                                  selected_power_lower=selected["protected_power_lower"],
                                  selected_false_alarm_upper=selected["false_alarm_upper"],
                                  selected_evidence_binding={k:selected.get(k,"NA") for k in BINDING_FIELDS},
                                  previous_H=grid[grid.index(h)-1] if grid.index(h) else None)
                    break
                predecessors_complete &= completed
            answers.append(answer)
    return answers

def build_report(csv_bytes,protocol_bytes):
    protocol_hash=hashlib.sha256(protocol_bytes).hexdigest()
    if protocol_hash!=PROTOCOL_SHA:raise MetadataCoverageError("Frozen protocol hash mismatch")
    protocol=json.loads(protocol_bytes.decode("utf-8-sig"));expected=expected_keys(protocol)
    if len(expected)!=400 or len(set(expected))!=400:raise MetadataCoverageError("Expected grid is not unique400")
    rows=list(csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"))))
    pairs=select_pairs(rows,protocol,expected)
    return {"protocol_sha256":protocol_hash,
            "scope":"declared finite grid/procedure; fixed fault template; inherited conditions; no minimax/continuous/sequential optimality",
            "review_bound_table_sha256":hashlib.sha256(csv_bytes).hexdigest(),
            "full_D2a_table_complete":all(r["risk_status"] in KNOWN for r in rows),"pairs":pairs,
            "metadata_guard":"EXACT_EXPECTED_400_KEYS_UNIQUE_NONEMPTY_CURRENT_GROUPS_SINGLE_CSV_BYTES",
            "rows":len(rows)}

def validate_physical_item(item):
    """Validate explicit calendar result and original clock; no nonlinear replay."""
    errors=[]
    if item.get("validation_errors"):errors.extend(item["validation_errors"])
    if item.get("physical_contract_validated") is not True:errors.append("NO_EXPLICIT_VALIDATION_PASS")
    try:
        if item["prefix_slots"]!=4 or item["T_fast_steps"]!=(item["H_post_slots"]+4)*250:
            errors.append("PREFIX_OR_TOTAL_CLOCK")
        moves=item["moves"]
        for i,(start,stop) in enumerate(moves):
            if stop-start!=1500 or stop+1500>item["T_fast_steps"]:errors.append("MOVE_OR_SETTLE_CLOCK")
            if (start if i==0 else start-moves[i-1][1])<1750:errors.append("REMOVE_BEFORE_1750")
        for obs in item["observations"]:
            start=obs["slot_zero_based"]*250
            if start<0 or start+250>item["T_fast_steps"]:errors.append("READ_OUTSIDE_TIME_BUDGET")
            if obs["point_index"]!=start+249 or obs["average_indices"]!=[start,start+250]:
                errors.append("READOUT_INDEX_CLOCK")
            completed=[stop for a,stop in moves if stop<=start]
            arrival=completed[-1] if completed else 0
            if obs["source_segment"]!=(not completed):errors.append("SOURCE_POST_SEGMENT")
            if obs["hold_start_age_steps"]!=start-arrival:errors.append("HOLD_AGE_CLOCK")
            if completed and start-arrival<1500:errors.append("READ_BEFORE_SETTLE")
    except (KeyError,TypeError,ValueError) as e:errors.append("MISSING_OR_INVALID_CLOCK:"+str(e))
    if errors:raise PhysicalContractError(";".join(sorted(set(errors))))
    return True

def apply_physical_guard(row,item):
    row["physical_rule_status"]="NOT_CHECKED"
    try:validate_physical_item(item)
    except PhysicalContractError:
        row.update(physical_rule_status="PHYSICAL_CONTRACT_FAILED",
                   risk_status="PHYSICAL_CONTRACT_FAILED",failure_classification="PHYSICAL_CONTRACT_FAILED")
        raise
    row["physical_rule_status"]="PASS_INHERITED_RULE_INSTANCE_CHECK"

def apply_preflight_failure(row,error,stage):
    if isinstance(error,PhysicalContractError) or stage=="physical":
        row.update(physical_rule_status="PHYSICAL_CONTRACT_FAILED",
                   direction_status="NOT_RUN_PHYSICAL_CONTRACT_FAILED",
                   risk_status="PHYSICAL_CONTRACT_FAILED",failure_classification="PHYSICAL_CONTRACT_FAILED")
    elif stage=="projection":
        row.update(direction_status="PROJECTION_CERTIFICATE_FAILED",
                   risk_status="PROJECTION_CERTIFICATE_FAILED",failure_classification="PROJECTION_CERTIFICATE_FAILED")
    else:
        row.update(risk_status="CERTIFICATION_EXECUTION_FAILED",failure_classification="PREFLIGHT_METADATA_FAILURE")
    row.update(failure_type=type(error).__name__,failure_message=str(error))
