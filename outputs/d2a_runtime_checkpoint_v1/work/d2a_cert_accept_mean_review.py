"""Bind the accepted independent review to the frozen actual fault template.

This records existing mathematical evidence; it does not repeat the reviewer
checks or broaden their scope to the full physical fault allowance.
"""
from pathlib import Path
from fractions import Fraction as F
import hashlib
import inspect
import json
import d2a_cert_case as core

report=core.ROOT/"outputs/d2a_mean_risk_review_v1.md"
assert report.exists()
plus=F("102094608476524939210343028899/336142366500000000000000000000")
minus=F("204198972606288391933745457097/672284733000000000000000000000")
assert plus<1 and minus<1
binding={"status":"ACCEPTED_FROZEN_TEMPLATE_MEAN_RISK_CHAIN","protocol_sha256":core.PROTOCOL_SHA,
         "report_path":"outputs/d2a_mean_risk_review_v1.md",
         "report_sha256":hashlib.sha256(report.read_bytes()).hexdigest(),
         "mean_function_after_scope_binding_sha256":hashlib.sha256(inspect.getsource(core.mean_certificate).encode("utf-8")).hexdigest(),
         "maximum_H_post_slots":600,"maximum_total_seconds":"151","actual_template_fault_max":"9/200",
         "fixed_template":"f(t)=3/10000*max(t-1,0), H0 f=0, h=1/1000, delta=1/4, 4 healthy prefix slots",
         "original_physical_fault_allowance_unchanged":"3/4",
         "mirror_equilibrium_inclusion_plus_max_ratio":str(plus),
         "mirror_equilibrium_inclusion_minus_max_ratio":str(minus),
         "source":"Independent review report section4: 16 saved beta cells, outward inverse, original Es; no new large adjoint verification",
         "wide_fault_0_75_mirror_containment_accepted":False,
         "inherited_conditions":["nonlinear remainder and event implications","rho-P/positive convolution certificates","segment component return","deterministic paths independent of innovations"],
         "risk_implementation_followup":"new wrapper returns conservative1 if a positive Mills score floors to0 on 1e-8 grid; boundary test passed; inherited source unchanged"}
core.atomic_text(core.ROOT/"work/d2a_cert_mean_review_binding.json",json.dumps(binding,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(binding,ensure_ascii=False))
