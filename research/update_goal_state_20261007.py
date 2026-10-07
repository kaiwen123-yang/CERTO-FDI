"""Record this goal turn's actual evidence, preserving inherited history."""
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]
def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
def write(path, obj):
    (ROOT / path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')
def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

now = datetime.now(timezone.utc).isoformat()
ledger = read('research/claims.json')
by_id = {c['id']: c for c in ledger['claims']}
by_id['IID-001'].update(status='SOURCE_RECOVERED_TWO_THEOREMS_REVIEWED_FIXES_PENDING_INTEGRATION', evidence=['references/manuscript_20260909/model.tex', 'references/manuscript_20260909/results.tex', 'references/manuscript_20260909/proof_sharp.tex', 'references/manuscript_20260909/proof_finite.tex', 'outputs/iid_independent_audit_v1.md', 'outputs/ar1_iid_audit_checks_v1.py', 'outputs/ar1_iid_audit_checks_v1.json', 'outputs/iid_source_recovery_v1.json'], review_version='2026-10-07 independent audit, hashes bound; constant-fault and mechanical chapters excluded', next_action='Integrate positive-part/risk range, final-k movement pairing and explicit m=0/global-joining clarifications into a working manuscript; keep source snapshot immutable.')
by_id['AR1-GAP-001'].update(status='NEW_EXACT_EXTENDED_LEMMAS_AND_RATIONAL_CHECKS', evidence=['outputs/ar1_information_lemmas_v1.md', 'outputs/ar1_information_lemmas_v1.tex', 'outputs/ar1_information_checks_v1.py', 'outputs/ar1_information_checks_v1.json'], review_version='2026-10-07 root algebra review plus exact finite checks; TeX compilation unverified', next_action='Use the exact raw boundary and affine reflection identities in the global proof; do not claim novelty of standard Markov/Schur tools.')
by_id['COLORED-SHARP-001'].update(status='CONVERSE_REVIEWED_MATCHING_UPPER_IN_PROGRESS', evidence=['outputs/problem_contract_v1.md', 'outputs/theorem_target_v1.md', 'outputs/colored_ar1_converse_v1.md', 'outputs/colored_ar1_converse_review_v1.md'], dependencies=['IID-001', 'AR1-GAP-001', 'COLORED-CONVERSE-001'], next_action='Construct a same-coefficient upper bound with full raw precision, finite support and preserved cross-block covariance; only then audit a sharp statement.')
by_id['D2A-001'].update(status='PROTOCOL_FROZEN_RECOVERY_QA_AND_CASE_CERTIFICATES_IN_PROGRESS', evidence=['outputs/d2a_protocol_v1.md', 'outputs/d2a_source_map_v1.md', 'outputs/d2a_certificate_progress_v1.md', 'work/d2a_PROTOCOL_v1.json', 'work/d2a_smoke_results.json', 'work/d2a_cert_checkpoint.json'], review_version='Protocol 0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6; uniform risk review and independent case verification pending', next_action='Complete first average/point uniform certificates and independent review, then all 400 declared rows; do not report H* before all earlier rows are certified or classified.')
new_claims = [
 {'id':'AR1-RAW-PROFILE-001','claim':'Retained bulk plus exact raw task/missing boundary and stationary endpoint terms approximates profiled AR(1) information with uniform O(H) error over the same complete unbounded-amplitude Lipschitz nuisance class.','status':'PROVED_WITH_ROOT_ALGEBRA_REVIEW','assumptions':['Common stationary known AR(1) covariance; fixed deterministic retained set','Signal Lipschitz constant and health difference rate fixed independently of H','All double-endpoint task terms retained; a jump at onset uses the appropriate finite signal Lipschitz envelope'], 'evidence':['outputs/ar1_information_lemmas_v1.md','outputs/ar1_information_checks_v1.py','outputs/ar1_information_checks_v1.json'],'review_version':'2026-10-07 Theorem H; root reviewed exact identity and inf inequality','dependencies':['AR1-GAP-001'],'next_action':'Do not delete boundary products; analyze the same variational problem for the upper construction.'},
 {'id':'AR1-BRIDGE-COUNTEREXAMPLE-001','claim':'A constant-gap beta replacement is not uniformly o(H^(5/2)) over every legal raw nuisance path in a specified full-sign extension.','status':'PROVED_COUNTEREXAMPLE_TO_WRONG_BRIDGE_ONLY','assumptions':['rho=1/2, sigma=1, k=1; J=sqrt(H) separated gaps','z=H constant, a=0, task flips across each gap','The chosen nuisance is not a profile minimizer; zero nuisance gives zero profiled information'],'evidence':['outputs/ar1_information_lemmas_v1.md','outputs/ar1_information_checks_v1.json'],'review_version':'2026-10-07 exact rational examples and symbolic derivation','dependencies':['AR1-GAP-001'],'next_action':'Use it to reject the all-path replacement method, not the main sharp coefficient.'},
 {'id':'COLORED-CONVERSE-001','claim':'Under fixed M0 parameters, n0>=1, B=infinity, deterministic known-horizon calendars, liminf D*/H^(5/2) >= sqrt(2)/5 sqrt(nu beta_k r) eta^(3/2).','status':'PROVED_INDEPENDENTLY_REVIEWED_WITH_CLARIFICATIONS','assumptions':['All problem_contract_v1 M0 assumptions','No alternative channels, third task, moving observations, adaptive calendar or required terminal task','Fixed rho in (-1,1), sigma>0, k>=1, eta,r>0','This is a lower bound, not a matching or finite-H theorem'],'evidence':['outputs/colored_ar1_converse_v1.md','outputs/colored_ar1_converse_review_v1.md','outputs/ar1_converse_checks_v1.py','outputs/ar1_converse_checks_v1.json'],'review_version':'Independent v1 acceptance; v1.1 adds D-tilde notation and global budget split. Current proof hash '+sha('outputs/colored_ar1_converse_v1.md'),'dependencies':['AR1-GAP-001'],'next_action':'Complete independent version binding after clarification and obtain matching upper construction.'},
 {'id':'CONTROL-MEMORY-001','claim':'For a common-input known first-order closed loop with deterministic x0=0 and q>0, full KL=Hd^2/(2q), while an internal missing gap loses d^2/(2q)(m-A_m^2/B_m).','status':'PROVED_TOOL_WITH_EXACT_FINITE_CHECKS','assumptions':['Known c=lambda-K with uniform stable admissible class','Same external constant input d, innovation q, horizon and retained outputs across controllers','No health profiling, extra measurement noise or free reconstruction from commands in this toy'],'evidence':['outputs/control_memory_example_v1.md','outputs/control_memory_checks_v1.py','outputs/control_memory_checks_v1.json'],'review_version':'2026-10-07 root proof and 16 exact deterministic-initialization matrix checks','dependencies':[],'next_action':'Map the drift/task input through the same physical filter and add observation/control constraints; do not substitute kappa into M0 without this mapping.'},
 {'id':'NOVELTY-M0-001','claim':'A finite targeted theorem audit records prior active feedback, controlled sensing, switching cost, full-history set separation and Gaussian convex testing; it does not prove exhaustive novelty.','status':'TARGETED_SOURCE_BACKED_AUDIT_WITH_EXPLICIT_GAPS','assumptions':['Bound to problem_contract_v1','Full text and abstract-only/NOT_OBTAINED items distinguished','Source theorem conditions and risk metrics preserved'],'evidence':['outputs/novelty_matrix.csv','outputs/novelty_audit_v1.md','work/literature_20261007/download_manifest.json','work/literature_audit_receipt.json'],'review_version':'2026-10-07 targeted primary-source audit','dependencies':[],'next_action':'Use restricted contribution wording and resolve the most relevant remaining theorem collisions as the physical M1 contract develops.'}
]
for c in new_claims:
    if c['id'] in by_id:
        by_id[c['id']].update(c)
    else:
        ledger['claims'].append(c)
ledger['updated_utc'] = now
ledger['purpose'] = 'Version-bound active research ledger. Proven tools, reviewed bounds, conjectures, source gaps and finite certificates have separate statuses.'
write('research/claims.json', ledger)

checkpoint = read('research/checkpoint.json')
checkpoint.update(updated_utc=now, phase='ACTIVE_M0_GLOBAL_PROOF_AND_D2A_CERTIFICATES', goal_active=True, goal_started_by_user=True, problem_contract_version='M0 v1 / '+sha('outputs/problem_contract_v1.md'), experiment_protocol_version='D2-a v1 / 0d8bed957fd152c256387c436de9472f878fc54018b2920bee30f04bd14033d6', previous_goal_turn_classification='INITIAL_GOAL_TURN_NO_PREVIOUS_GOAL_WORK', current_turn_classification='PROGRESS', last_substantive_result='Original iid sources recovered and two main theorems independently reviewed; exact raw AR1 boundary/profile lemmas and reviewed all-calendar converse; common-input control gap tool; frozen D2-a protocol, recovery QA and first uniform certificates in progress; targeted theorem matrix.', current_blocker=None, consecutive_goal_turns_with_same_blocker=0)
checkpoint['next_actions'] = [
 {'priority':1,'action':'Complete and independently audit the matching AR1 upper construction using full raw precision; bind the reviewed converse v1.1.','target_outputs':['outputs/ar1_upper_construction_v1.md'],'claims':['COLORED-SHARP-001','COLORED-CONVERSE-001']},
 {'priority':2,'action':'Finish first average/point uniform certificates and mean/risk review, then extend the frozen D2-a full candidate table with all failures.','target_outputs':['outputs/d2a_certificate_progress_v1.md','outputs/d2a_mean_risk_review_v1.md'],'claims':['D2A-001']},
 {'priority':3,'action':'Develop the physically consistent drift/task/control bridge M1 and integrate audited iid fixes into the future working manuscript; preserve originals.','target_outputs':['outputs/control_memory_example_v1.md'],'claims':['CONTROL-MEMORY-001','IID-001','NOVELTY-M0-001']}
]
checkpoint['running_processes'] = [
 {'owner':'/root/d2a_recovery','session_id':40244,'command':'python -S work/d2a_cert_verify.py (see case checkpoint and agent report)','purpose':'Independent stdlib verification of H120 average certificate','handle_status':'Confirmed live by owning agent; re-poll the same handle before any restart'},
 {'owner':'/root/d2a_recovery','session_id':93252,'command':'python -B -X utf8 work/d2a_cert_case.py --H 120 --readout point_last_fast_read','purpose':'H120 point certificate generation','handle_status':'Confirmed live by owning agent; re-poll the same handle before any restart'}
]
checkpoint['agent_tasks'] = [{'agent':'/root/ar1_proof','task':'Matching upper bound and converse clarification binding'}, {'agent':'/root/d2a_recovery','task':'New uniform certificates and stored-evidence verification'}, {'agent':'/root/novelty_theorems','task':'Independent D2-a mean/risk derivation review'}]
checkpoint['recovery_notes'] = ['The pasted objective is the original research plan, read at the initial goal turn. Goal is active; no completion or blocking claim.', 'Inspect actual sessions and owning agents before treating a job as stopped. An observation timeout does not authorize restarting.', 'Inputs/reference source snapshots immutable; formal evidence scripts/receipts now also in outputs.', 'AR1 TeX native compiler returned platform standard-directory error. Source preserved; compilation unverified, no alternate TeX installed.', 'Current reviewed bound does not complete the main sharp theorem, physical control bridge, full D2-a table or submission manuscript.']
write('research/checkpoint.json', checkpoint)

index = read('source_index.json')
receipt = read('outputs/iid_source_recovery_v1.json')
archive_name = 'CERTO_FDI_TAC_ADMISSION_REVISION_20260909'
for p in sorted((ROOT / 'references/manuscript_20260909').glob('*.tex')):
    member = archive_name + '/manuscript/' + p.name
    match = next(e for e in receipt['extracted_texts'] if e['member'] == member)
    digest = sha(p.relative_to(ROOT))
    assert digest == match['sha256']
    relative = p.relative_to(ROOT).as_posix()
    if not any(e['path'] == relative for e in index['files']):
        index['files'].append({'path':relative,'source_archive':receipt['archive_path'],'source_archive_sha256':receipt['archive_sha256'],'source_member':member,'kind':'original_manuscript_text_snapshot','bytes':p.stat().st_size,'sha256':digest,'source_sha256':digest,'byte_identical':True})
index['file_count'] = len(index['files'])
index['generated_utc'] = now
write('source_index.json', index)
print(json.dumps({'claims':len(ledger['claims']),'source_entries':index['file_count'],'phase':checkpoint['phase']}))
