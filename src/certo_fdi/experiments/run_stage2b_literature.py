"""Stage 2B Phase 5: bounded literature verification (kickoff §09).

The protocol permits the experiments to run offline but forbids *upgrading* any novelty claim
without a primary-source search. The execution host turned out to have a route to primary
sources, so the bounded search was run rather than the offline fallback, and this runner records
what it actually found.

Two limits are stated up front because they bound how the result may be read:

* **abstract-level, not full-text.** The evidence rules ask for full-text reading of direct
  collisions. Most hits were reachable only as landing pages or as PDFs the fetcher could not
  convert, so the findings below rest on abstracts, publisher metadata and search-engine
  extracts. The record is therefore ``PERFORMED_PARTIAL``, never ``COMPLETE``.
* **downgrades only.** A partial search may *tighten* a novelty status -- if prior art is found,
  it is found -- but it may never loosen one. Every claim that was not positively resolved stays
  at ``PLAUSIBLY_OPEN / NOT_ESTABLISHED``.

No citation, DOI or venue in this file was reconstructed from memory; each one is recorded with
the URL it was read from. The word "first" is not used about any Stage 2B result.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

from certo_fdi.experiments.common import utc_now, write_csv, write_json
from certo_fdi.experiments.stage2b_common import Stage, common_parser

#: kickoff §09.1 -- the six topics a Stage 2B novelty claim could collide with
TOPICS = [
    ("T1", "serial-chain load-path collision isolation / virtual power"),
    ("T2", "Jacobian or kinetostatic projection contact-link localization"),
    ("T3", "rank-aware nested subspace model selection for contact localization"),
    ("T4", "context-conditioned robot collision/anomaly thresholds"),
    ("T5", "sequential collision monitoring with false alarms/hour or ARL"),
    ("T6", "ambiguity-aware reject/defer contact localization"),
]

#: kickoff §09.2 -- verbatim
SEARCH_STRINGS = [
    '"serial manipulator" contact link isolation virtual power',
    '"load path" collision localization robot manipulator',
    "Jacobian projection contact link localization proprioception",
    "kinetostatic projection collision isolation manipulator",
    "context conditioned threshold robot collision detection",
    "false alarms per hour robot collision detection",
    "sequential CUSUM manipulator collision detection",
    "selective contact localization reject option robot",
    "ambiguity aware contact localization robot arm",
]

PRIORITY_VENUES = ["T-RO", "IJRR", "RA-L", "T-Mech", "TIE", "Automatica", "TAC", "ICRA", "IROS", "RSS"]

#: the Stage 2B statements whose novelty status this phase governs
NOVELTY_CLAIMS = [
    ("N1", "serial-chain prefix support is the dominant carrier of contact-link localization signal, with "
           "Cartesian subspace shape a measurable secondary term"),
    ("N2", "rank-matched synthetic controls (DCT and random orthonormal frames inside the same support) can "
           "separate support gain from subspace-shape gain in contact localization"),
    ("N3", "episode-blocked conformal calibration plus a one-sided CUSUM reduces event false alarms per hour by "
           "more than an order of magnitude on a context-shifted healthy set"),
    ("N4", "an ambiguity-aware accept/defer rule for contact-link localization calibrated on a separate contact "
           "partition"),
]

#: sources actually consulted, with the URL each fact was read from. Depth is recorded honestly:
#: "abstract" means the abstract or publisher metadata was read, not the full text.
SOURCES = [
    {"id": "S1", "topics": ["T1", "T2"],
     "citation": "S. Haddadin, A. De Luca, A. Albu-Schaffer, \"Robot Collisions: A Survey on Detection, "
                 "Isolation, and Identification\", IEEE Transactions on Robotics 33(6):1292-1312, 2017",
     "doi": "10.1109/TRO.2017.2723903", "venue": "T-RO", "year": 2017, "status": "published",
     "url": "https://ieeexplore.ieee.org/abstract/document/8059840",
     "depth": "abstract + publisher metadata + secondary description",
     "overlap": ("Establishes the standard proprioceptive collision isolation rule for open kinematic chains: "
                 "a contact on link i produces external joint torques only at joints up to i, so the contact "
                 "link is taken as the most distal joint whose external torque exceeds a threshold. This is "
                 "exactly the prefix-support structure Stage 2B measures."),
     "consequence": "N1's structural premise is established prior art, not a Stage 2B finding."},
    {"id": "S2", "topics": ["T2"],
     "citation": "A. Mohammad et al., \"Collision Isolation and Identification Using Proprioceptive Sensing "
                 "for Parallel Robots to Enable Human-Robot Collaboration\", arXiv:2308.09650, 2023",
     "doi": "10.48550/arXiv.2308.09650", "venue": "arXiv (IROS-class)", "year": 2023, "status": "preprint",
     "url": "https://arxiv.org/pdf/2308.09650",
     "depth": "abstract + secondary description; full-text fetch returned unconverted PDF",
     "overlap": ("Uses a kinetostatic projection with Jacobian matrices to project external forces onto "
                 "actuated joint coordinates in order to classify which body was collided, and trains a "
                 "feedforward classifier on the resulting physically modelled features."),
     "consequence": ("Jacobian-transpose projection as a contact-body classification feature is prior art. "
                     "Stage 2B's contribution can only be the controlled decomposition, not the projection.")},
    {"id": "S3", "topics": ["T3"],
     "citation": "M. N. Tabassum, E. Ollila, \"Simultaneous Signal Subspace Rank and Model Selection with an "
                 "Application to Single-snapshot Source Localization\", arXiv:1806.07320, 2018",
     "doi": "10.48550/arXiv.1806.07320", "venue": "arXiv / IEEE conference", "year": 2018, "status": "published",
     "url": "https://arxiv.org/abs/1806.07320",
     "depth": "abstract + secondary description",
     "overlap": ("Selects subspace rank and model jointly over a nested sequence of regression models using a "
                 "generalized information criterion -- the same statistical problem shape as Stage 2B's "
                 "rank-aware scoring over nested link supports, but in array processing, not robot contact."),
     "consequence": ("Rank-aware nested subspace selection is established statistics. Its application to "
                     "serial-chain contact-link localization was not found; N2 stays open but unproven.")},
    {"id": "S4", "topics": ["T4", "T5"],
     "citation": "\"Reducing false alarms in fault detection: A comparative analysis between conformal "
                 "prediction and classical methods applied to PCA and autoencoders\", Control Engineering "
                 "Practice (ScienceDirect S0959152425001234), 2025",
     "doi": "", "venue": "Control Engineering Practice", "year": 2025, "status": "published",
     "url": "https://www.sciencedirect.com/science/article/abs/pii/S0959152425001234",
     "depth": "abstract + secondary description",
     "overlap": ("Uses conformal prediction with marginal and conditional validity to set fault-detection "
                 "thresholds and calibrate the false-alarm rate without distributional assumptions."),
     "consequence": ("Conformal calibration of a fault-detection false-alarm rate is prior art. N3 cannot rest "
                     "on the calibration idea itself.")},
    {"id": "S5", "topics": ["T4"],
     "citation": "\"Learning Robot Safety from Sparse Human Feedback using Conformal Prediction\", "
                 "arXiv:2501.04823, 2025",
     "doi": "10.48550/arXiv.2501.04823", "venue": "arXiv", "year": 2025, "status": "preprint",
     "url": "https://arxiv.org/pdf/2501.04823",
     "depth": "abstract + secondary description",
     "overlap": "Applies conformal prediction as a distribution-free method for robot safety and anomaly detection.",
     "consequence": "Confirms conformal calibration is already in use in robotics safety monitoring."},
    {"id": "S6", "topics": ["T6"],
     "citation": "Y. Geifman, R. El-Yaniv, \"Selective Classification for Deep Neural Networks\", "
                 "arXiv:1705.08500, NeurIPS 2017",
     "doi": "10.48550/arXiv.1705.08500", "venue": "NeurIPS", "year": 2017, "status": "published",
     "url": "https://arxiv.org/abs/1705.08500",
     "depth": "abstract + secondary description",
     "overlap": ("Defines the risk-coverage formulation of selective classification with a reject option that "
                 "Stage 2B's accept/defer rule uses directly."),
     "consequence": ("The reject-option machinery is prior art. Only its use on contact-link localization, "
                     "calibrated on a separate contact partition, was not found.")},
    {"id": "S7", "topics": ["T5"],
     "citation": "\"Disturbance Recognition and Collision Detection of Manipulator Based on Momentum "
                 "Observer\", Sensors 20(15):4187, 2020",
     "doi": "10.3390/s20154187", "venue": "Sensors", "year": 2020, "status": "published",
     "url": "https://www.mdpi.com/1424-8220/20/15/4187",
     "depth": "abstract + secondary description",
     "overlap": ("Describes the standard threshold trade-off in momentum-observer collision detection: the "
                 "threshold must be raised to suppress false alarms, which costs sensitivity."),
     "consequence": ("The false-alarm/sensitivity trade-off is well known. No manipulator collision-detection "
                     "paper reporting an explicit false-alarms-per-hour or ARL0 operating point was found in "
                     "this bounded search, but absence in a bounded search is not evidence of absence.")},
]

#: per-claim verdicts. A partial search may tighten a status but may never loosen one.
CLAIM_VERDICTS = {
    "N1": {"status": "PRIOR_ART_FOUND",
           "sources": ["S1", "S2"],
           "note": ("The prefix-support structure and Jacobian-transpose projection are both standard. Stage 2B "
                    "may report that it *measured* how the localization signal splits between them; it may not "
                    "present either mechanism as new.")},
    "N2": {"status": "PLAUSIBLY_OPEN / NOT_ESTABLISHED",
           "sources": ["S3"],
           "note": ("Rank-aware nested subspace selection is established in array processing; no application to "
                    "serial-chain contact-link localization with rank-matched synthetic controls was found. The "
                    "search was abstract-level only, so this is unresolved, not clear.")},
    "N3": {"status": "PLAUSIBLY_OPEN / NOT_ESTABLISHED",
           "sources": ["S4", "S5", "S7"],
           "note": ("Conformal false-alarm calibration and CUSUM change detection are both prior art. The "
                    "specific combination -- episode-blocked conformal calibration plus a one-sided CUSUM, "
                    "evaluated in event false alarms per hour on a context-shifted healthy manipulator set -- "
                    "was not found, but the components are not new and the Stage 2B result did not meet its "
                    "own target, so nothing here is claimed.")},
    "N4": {"status": "PLAUSIBLY_OPEN / NOT_ESTABLISHED",
           "sources": ["S6"],
           "note": ("Selective classification with a reject option is prior art; its use for contact-link "
                    "localization with thresholds calibrated on a separate contact partition was not found.")},
}

PROBE_HOSTS = [("doi.org", 443), ("api.crossref.org", 443), ("arxiv.org", 443),
               ("api.semanticscholar.org", 443), ("ieeexplore.ieee.org", 443)]


def _probe(timeout: float = 4.0) -> dict:
    """Is any primary-source host reachable? DNS first, then a TLS connect, then one HTTP HEAD."""
    results = []
    reachable = False
    for host, port in PROBE_HOSTS:
        row = {"host": host, "port": port, "dns": False, "tcp": False, "http": False, "error": ""}
        try:
            socket.getaddrinfo(host, port)
            row["dns"] = True
            with socket.create_connection((host, port), timeout=timeout):
                row["tcp"] = True
            req = urllib.request.Request(f"https://{host}/", method="HEAD",
                                         headers={"User-Agent": "CERTO-FDI-stage2b-literature-probe"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                row["http"] = 200 <= r.status < 500
        except (socket.gaierror, OSError, urllib.error.URLError, ValueError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"[:160]
        reachable = reachable or row["http"]
        results.append(row)
    return {"reachable": reachable, "probes": results, "probed_utc": utc_now()}


def _not_performed_md(probe: dict, run_id: str, status: str) -> str:
    """What the bounded protocol still owes, given what this run could and could not do."""
    offline = not probe["reachable"]
    lines = [
        "# Bounded literature verification: what was NOT performed",
        "",
        f"Run `{run_id}` · {utc_now()} · status `{status}`",
        "",
    ]
    if offline:
        lines += [
            "## Nothing was performed",
            "",
            "The execution host had no reachable route to any primary-source service, so no source was consulted",
            "and no DOI, venue or publication status could be verified. The kickoff protocol (§09, evidence rules)",
            "covers this case explicitly: write this file and keep novelty at `PLAUSIBLY_OPEN / NOT_ESTABLISHED`.",
            "",
        ]
    else:
        lines += [
            "## The search ran; the full-text step did not",
            "",
            "Primary sources were reachable and the bounded search was executed, so this is **not** the offline",
            "fallback. What was not done is the part of the evidence rules that asks for full-text reading of every",
            "direct collision: most hits were reachable only as landing pages, paywalled records or PDFs the",
            "fetcher could not convert to text. Every finding in `stage2b_literature_verification.md` therefore",
            "rests on abstracts, publisher metadata and search-engine extracts, and each source records its own",
            "reading depth.",
            "",
            "Consequences, stated so they cannot be quietly forgotten:",
            "",
            "- a claim recorded as `PRIOR_ART_FOUND` is safe -- finding prior art in an abstract is sufficient to",
            "  *retire* a novelty claim, and N1 is retired on that basis;",
            "- a claim left at `PLAUSIBLY_OPEN / NOT_ESTABLISHED` is **unresolved**, not cleared. An abstract-level",
            "  sweep of nine search strings cannot establish absence;",
            "- no status was loosened by this run. A partial search may only tighten.",
            "",
        ]
    lines += [
        "## Probe results",
        "",
        "| host | DNS | TCP | HTTP | error |",
        "|---|---|---|---|---|",
    ]
    for p in probe["probes"]:
        lines.append(f"| `{p['host']}` | {'yes' if p['dns'] else 'no'} | {'yes' if p['tcp'] else 'no'} | "
                     f"{'yes' if p['http'] else 'no'} | `{p['error'] or '-'}` |")
    lines += [
        "",
        "## What remains to be done",
        "",
        "The search is fully specified, so it can be completed later without re-deriving anything. Re-run the",
        "strings in `stage2b_literature_verification.md` §3 against the priority venues in §4, obtain the full",
        "text of every direct collision (institutional access is needed for the T-RO and Control Engineering",
        "Practice records), and record DOI / status / venue / data / code / exact overlap per hit.",
        "",
        "Specifically still open:",
        "",
        "- whether any published work applies **rank-aware nested subspace selection** to contact-link",
        "  localization on a serial chain (claim N2);",
        "- whether any manipulator collision-detection paper reports an explicit **false-alarms-per-hour or ARL0**",
        "  operating point that Stage 2B's numbers could be compared against (claim N3);",
        "- whether a **reject/defer option** has been applied to contact-link localization before (claim N4).",
        "",
        "Until that is done the Stage 2B claims are stated as *what this experiment measured*, never as *what",
        "nobody has measured before*. The word \"first\" is not used about any Stage 2B result.",
        "",
    ]
    return "\n".join(lines)


def _verification_md(probe: dict, run_id: str, status: str) -> str:
    lines = [
        "# Stage 2B bounded literature verification",
        "",
        f"Run `{run_id}` · generated {utc_now()} · **status: `{status}`**",
        "",
        "## 1. Standing rule",
        "",
        "Stage 2A performed no online literature verification, so every Stage 2B novelty claim starts at",
        "`NOT_ESTABLISHED` and may only be upgraded by a bounded primary-source search. This document is the",
        "record of that search -- including the case where it could not be run.",
        "",
        "## 2. Topics in scope",
        "",
        "| id | topic |",
        "|---|---|",
    ]
    lines += [f"| {tid} | {t} |" for tid, t in TOPICS]
    lines += ["", "## 3. Search strings (verbatim from the kickoff protocol)", "", "```text"]
    lines += SEARCH_STRINGS
    lines += ["```", "", "## 4. Priority venues", "", ", ".join(PRIORITY_VENUES) + ".", "",
              "Full text is read for direct collisions; DOI, status, venue, data and code availability, and the",
              "exact overlap are recorded per hit.", "",
              "## 5. Reachability probe", "",
              f"Primary sources reachable from this host: **{'yes' if probe['reachable'] else 'no'}**.", ""]
    if not probe["reachable"]:
        lines += ["Every probe failed (see `NOT_PERFORMED.md` for the per-host detail), so **no source was",
                  "consulted**. The results table below is therefore empty by construction, not by absence of",
                  "prior work -- the correct reading is *unknown*, not *nothing exists*.", ""]
    offline = not probe["reachable"]
    lines += ["## 6. Sources consulted", ""]
    if offline:
        lines += ["None. See `NOT_PERFORMED.md`.", ""]
    else:
        lines += ["Reading depth is stated per source. \"abstract\" means the abstract, publisher metadata or a",
                  "search-engine extract was read -- **not** the full text.", "",
                  "| id | topics | citation | DOI | venue | year | depth |", "|---|---|---|---|---|---|---|"]
        for s in SOURCES:
            lines.append(f"| {s['id']} | {', '.join(s['topics'])} | {s['citation']} | "
                         f"`{s['doi'] or 'n/a'}` | {s['venue']} | {s['year']} | {s['depth']} |")
        lines += ["", "### Exact overlap with Stage 2B", ""]
        for s in SOURCES:
            lines += [f"**{s['id']}** — {s['overlap']}", "", f"> Consequence for Stage 2B: {s['consequence']}", ""]

    lines += ["## 7. Per-topic outcome", "", "| topic | sources | outcome |", "|---|---|---|"]
    by_topic: dict[str, list[str]] = {t: [] for t, _ in TOPICS}
    for s in SOURCES:
        for t in s["topics"]:
            by_topic.setdefault(t, []).append(s["id"])
    outcomes = {
        "T1": "direct collision: the prefix-support isolation rule is standard prior art",
        "T2": "direct collision: Jacobian/kinetostatic projection for contact-body classification is prior art",
        "T3": "adjacent field only: nested-subspace rank selection is established, not on contact localization",
        "T4": "direct collision: conformal and context-conditioned fault-detection thresholds are prior art",
        "T5": "no comparable operating point found; the false-alarm/sensitivity trade-off itself is standard",
        "T6": "adjacent field only: selective classification is established, not on contact-link localization",
    }
    for tid, _ in TOPICS:
        srcs = ", ".join(by_topic.get(tid, [])) or "none"
        lines.append(f"| {tid} | {srcs} | {'not assessed (offline)' if offline else outcomes.get(tid, '')} |")

    lines += ["", "## 8. Novelty status of the Stage 2B claims", "",
              "| id | claim | status | basis |", "|---|---|---|---|"]
    for cid, c in NOVELTY_CLAIMS:
        v = CLAIM_VERDICTS[cid] if not offline else {"status": "PLAUSIBLY_OPEN / NOT_ESTABLISHED", "sources": [], "note": "search not performed"}
        lines.append(f"| {cid} | {c} | `{v['status']}` | {', '.join(v['sources']) or 'n/a'} |")
    lines += [""]
    if not offline:
        for cid, _ in NOVELTY_CLAIMS:
            lines += [f"**{cid}** — {CLAIM_VERDICTS[cid]['note']}", ""]
    lines += [
        "`PRIOR_ART_FOUND` retires a novelty claim: an abstract is enough to show that something exists.",
        "",
        "`PLAUSIBLY_OPEN / NOT_ESTABLISHED` means only that this bounded, abstract-level search did not find an",
        "identical published protocol. It is **not** evidence of absence and carries no priority claim. Nothing",
        "was upgraded by this run.",
        "",
        "## 9. Language constraints in force",
        "",
        "- the word \"first\" is not used about any Stage 2B result;",
        "- no exact conditional CFAR guarantee is claimed;",
        "- no physical wrench is claimed to be recovered from network-internal messages;",
        "- no universal link identifiability is claimed;",
        "- the prefix-support structure and the Jacobian-transpose projection are described as **standard**,",
        "  with Stage 2B contributing only their controlled quantitative separation;",
        "- prior-art status stays `NOT_ESTABLISHED` until a completed full-text search says otherwise.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = common_parser("Stage 2B Phase 5: bounded literature verification")
    ap.add_argument("--assume-offline", action="store_true",
                    help="skip the network probe and record NOT_PERFORMED directly")
    args = ap.parse_args()
    st = Stage(args, "literature")
    if not st.require_freeze():
        return 3

    probe = {"reachable": False, "probes": [{"host": h, "port": p, "dns": False, "tcp": False, "http": False,
                                             "error": "probe skipped (--assume-offline)"} for h, p in PROBE_HOSTS],
             "probed_utc": utc_now()} if args.assume_offline else _probe()
    st.log(f"primary-source reachability: {probe['reachable']}")
    for p in probe["probes"]:
        st.log(f"  {p['host']}: dns={p['dns']} tcp={p['tcp']} http={p['http']} {p['error']}")

    # A reachable host permits the bounded search, but the full-text step of the evidence rules was
    # only partly possible, so the record is PERFORMED_PARTIAL -- never COMPLETE.
    offline = not probe["reachable"]
    status = "NOT_PERFORMED_OFFLINE" if offline else "PERFORMED_PARTIAL_ABSTRACT_LEVEL"
    sources = [] if offline else SOURCES
    verdicts = ({cid: {"status": "PLAUSIBLY_OPEN / NOT_ESTABLISHED", "sources": [], "note": "search not performed"}
                 for cid, _ in NOVELTY_CLAIMS} if offline else CLAIM_VERDICTS)

    out = st.layout.results
    (out / "stage2b_literature_verification.md").write_text(_verification_md(probe, st.layout.run_id, status),
                                                            encoding="utf-8")
    (out / "NOT_PERFORMED.md").write_text(_not_performed_md(probe, st.layout.run_id, status), encoding="utf-8")
    write_json(out / "stage2b_literature_probe.json",
               {"status": status, "reachable": probe["reachable"], "probes": probe["probes"],
                "topics": [{"id": t, "topic": d} for t, d in TOPICS],
                "search_strings": SEARCH_STRINGS, "priority_venues": PRIORITY_VENUES,
                "sources": sources, "n_sources_read": len(sources),
                "n_full_text_read": 0,
                "reading_depth": "abstract / publisher metadata / search-engine extract only",
                "novelty_claims": [{"id": c, "claim": d, **verdicts[c]} for c, d in NOVELTY_CLAIMS],
                "first_language_used": False,
                "note": ("a partial search may tighten a novelty status but never loosen one; "
                         "PLAUSIBLY_OPEN means unresolved, not cleared -- absence in a bounded "
                         "abstract-level search is not evidence of absence")})
    st.write_table("stage2b_literature_claims.csv",
                   [st.base_row(method=cid, partition="literature", split="ALL", claim=c,
                                novelty_status=verdicts[cid]["status"],
                                basis=",".join(verdicts[cid]["sources"]),
                                note=verdicts[cid]["note"],
                                n_sources_read=len(sources), n_full_text_read=0,
                                search_status=status, empirical=False, strict=False,
                                status=("PRIOR_ART_FOUND" if verdicts[cid]["status"] == "PRIOR_ART_FOUND"
                                        else "NOT_ESTABLISHED"))
                    for cid, c in NOVELTY_CLAIMS],
                   units="one row per Stage 2B novelty claim",
                   schema={"novelty_status": "PRIOR_ART_FOUND retires a claim; PLAUSIBLY_OPEN means unresolved"})
    st.write_table("stage2b_literature_sources.csv",
                   [st.base_row(method=s["id"], partition="literature", split="ALL",
                                topics=";".join(s["topics"]), citation=s["citation"], doi=s["doi"],
                                venue=s["venue"], year=s["year"], source_status=s["status"], url=s["url"],
                                depth=s["depth"], overlap=s["overlap"], consequence=s["consequence"],
                                empirical=False, strict=False, status="OK")
                    for s in sources],
                   units="one row per source consulted",
                   schema={"depth": "abstract-level unless it says full text"})
    retired = [c for c, _ in NOVELTY_CLAIMS if verdicts[c]["status"] == "PRIOR_ART_FOUND"]
    st.log(f"literature verification recorded: {status} ({len(sources)} sources, 0 full texts); "
           f"claims retired by prior art: {retired or 'none'}")
    st.finish({"literature_status": status, "n_sources": len(sources), "claims_retired": retired})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
