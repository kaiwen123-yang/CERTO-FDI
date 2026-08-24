"""Phase L40/L100: resolve V2 full-text targets through the frozen access ladder.

Reuses the V1 ladder (certo_fdi_reset.literature.fulltext): OpenAlex/Crossref
metadata -> institutional repository (OpenAIRE / S2 openAccessPdf) -> author
manuscript (Unpaywall repository locations) -> arXiv cross-checked -> OA
locations. No access control is bypassed; a miss is FULLTEXT_UNAVAILABLE and
never supports OPEN/OCCUPIED.

Targets below are the L500 screening's INCLUDE_PRIORITY set plus the
direction-setting cross-robot/context/MTSAD picks. V1's ten Wave A texts are
inherited (PORT_PROVENANCE.md) and not re-fetched.

    python -m certo_fdi_reset_v2.literature.acquire_wave [--only id1,id2]
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import requests

from certo_fdi_reset.literature.fulltext import (
    MANIFEST_COLUMNS,
    Resolution,
    Target,
    USER_AGENT,
    extract_text,
    fetch_fulltext,
    render_negative_search_log,
    resolve_arxiv,
    resolve_openaire,
    resolve_openalex,
    resolve_semantic_scholar,
    resolve_unpaywall,
)

V2_FULLTEXT_ROOT = Path("/mnt/g/CERTO-FDI/01_frozen_sources/literature_reset_v2")
OUT_DIR = V2_FULLTEXT_ROOT / "open_fulltexts"
MANIFEST_DIR = V2_FULLTEXT_ROOT / "access_manifest"
RUN_ID = "run_20260824T023044Z_paper_reset_v2"

# role: killer | neighbor | dataset | crossrobot | mtsad | review | classic
WAVE_V2A: tuple[Target, ...] = (
    # --- killer / nearest-neighbour / dataset (target: 25+) ---
    Target("kim_lim_park_tro21", "Transferable Collision Detection Learning for Collaborative Manipulator Using Versatile Modularized Neural Network", doi="10.1109/tro.2021.3129630", role="killer", why_wave_a="contract-listed killer; V1 unavailable, retry"),
    Target("park_unsup_tmech22", "Collision Detection for Robot Manipulators Using Unsupervised Anomaly Detection Algorithms", doi="10.1109/tmech.2021.3119057", role="killer", why_wave_a="contract-listed killer; V1 unavailable, retry"),
    Target("ur5e_graabaek_access23", "An Experimental Comparison of Anomaly Detection Methods for Collaborative Robot Manipulators", doi="10.1109/access.2023.3289068", role="dataset", why_wave_a="supplementary dataset paper, richest P2 set"),
    Target("pr_fast_contact_ral25", "Fast Contact Detection Via Fusion of Joint and Inertial Sensors for Parallel Robots in Human-Robot Collaboration", doi="10.1109/lra.2025.3575326", role="neighbor", why_wave_a="2025 proprioceptive+IMU contact detection"),
    Target("payload_adaptive_timc24", "Adaptive collision detection algorithm design for six-axis industrial manipulator with accurate payload estimation", doi="10.1177/01423312241239375", role="neighbor", why_wave_a="payload/context-varying collision threshold"),
    Target("nonlinear_mob_mech21", "A nonlinear momentum observer for sensorless robot collision detection under model uncertainties", doi="10.1016/j.mechatronics.2021.102603", role="neighbor", why_wave_a="MOB under model uncertainty, core L3"),
    Target("multicontact_icra23", "Proprioceptive Sensor-Based Simultaneous Multi-Contact Point Localization and Force Identification for Robotic Arms", doi="10.1109/icra48891.2023.10161173", role="neighbor", why_wave_a="proprioceptive multi-contact localization"),
    Target("mob_lstm_icra21", "Momentum Observer-Based Collision Detection Using LSTM for Model Uncertainty Learning", doi="10.1109/icra48506.2021.9561667", role="neighbor", why_wave_a="learned MOB uncertainty (Korean line)"),
    Target("delan_mob_rcim26", "Improved deep Lagragian network-enabled momentum observer for collision detection during human-robot collaboration", doi="10.1016/j.rcim.2025.103093", role="neighbor", why_wave_a="DeLaN-structured learned MOB"),
    Target("sara_redundant_icra21", "Collision Detection, Identification, and Localization on the DLR SARA Robot with Sensing Redundancy", doi="10.1109/icra48506.2021.9561677", role="neighbor", why_wave_a="DLR extended MOB with F/T redundancy"),
    Target("physics_rnn_aei24", "Hybrid physics-embedded recurrent neural networks for fault diagnosis under time-varying conditions based on multivariate proprioceptive signals", doi="10.1016/j.aei.2024.102851", role="neighbor", why_wave_a="physics-embedded RNN + condition shift"),
    Target("mb_vs_mf_delta_cep23", "Model-based and model-free collision detection and identification for a parallel Delta robot with uncertainties", doi="10.1016/j.conengprac.2023.105663", role="neighbor", why_wave_a="estimator-family comparison under uncertainty"),
    Target("vla_joint_faults_2026", "Uncovering Vulnerability of Vision-Language-Action Models under Joint-Level Physical Faults", role="neighbor", why_wave_a="VLA x embodiment faults, newest intersection"),
    Target("llm_ad_rss24", "Real-Time Anomaly Detection and Reactive Planning with Large Language Models", doi="10.15607/rss.2024.xx.114", role="neighbor", why_wave_a="foundation-model runtime robot AD"),
    Target("aim_aware_ral23", "Aim-Aware Collision Monitoring: Discriminating Between Expected and Unexpected Post-Impact Behaviors", doi="10.1109/lra.2023.3284371", role="neighbor", why_wave_a="expected-vs-unexpected impact discrimination"),
    Target("contact_loc_motion_icra21", "Contact Localization for Robot Arms in Motion without Torque Sensing", doi="10.1109/icra48506.2021.9562058", role="neighbor", why_wave_a="proprioceptive-only contact localization"),
    Target("ras26_serial_fd_review", "Fault detection for serial robotic manipulators: A review", doi="10.1016/j.robot.2026.105611", role="review", why_wave_a="newest dedicated field review, coverage anchor"),
    Target("coffail_2026", "COFFAIL: A Dataset of Successful and Anomalous Robot Skill Executions in the Context of Coffee Preparation", role="dataset", why_wave_a="new 2026 robot-anomaly dataset"),
    Target("modal_mob_ijrr25", "A modal-space formulation for momentum observer contact estimation and effects of uncertainty for continuum robots", doi="10.1177/02783649251342823", role="neighbor", why_wave_a="MOB generalization frontier + uncertainty"),
    Target("pr_isolation_iros23", "Collision Isolation and Identification Using Proprioceptive Sensing for Parallel Robots to Enable Human-Robot Collaboration", doi="10.1109/iros55552.2023.10342345", role="neighbor", why_wave_a="proprioceptive isolation on real PR"),
    Target("hybrid_gmo_iros25", "Hybrid Data-Model-Driven External Force Estimation for Manipulators via Generalized Momentum-Based Third-Order Observer", doi="10.1109/iros60139.2025.11245923", role="neighbor", why_wave_a="MLP residual + 3rd-order GMO"),
    Target("dob_friction_rcim21", "Sensorless force estimation for industrial robots using disturbance observer and neural learning of friction approximation", doi="10.1016/j.rcim.2021.102168", role="neighbor", why_wave_a="DOB + learned friction residual"),
    Target("se2_equiv_zenodo26", "SE2-Equivariant-Fault-Detection-Robotic-Arm", doi="10.5281/zenodo.21627629", role="killer", why_wave_a="direct occupancy probe of equivariance-residual idea"),
    Target("virtual_jts_icra23", "Collision Detection and Contact Point Estimation Using Virtual Joint Torque Sensing Applied to a Cobot", doi="10.1109/icra48891.2023.10160661", role="neighbor", why_wave_a="energy+momentum combined on industrial cobot"),
    Target("legged_manip_iros22", "Collision detection and identification for a legged manipulator", doi="10.1109/iros47612.2022.9981767", role="neighbor", why_wave_a="floating-base variant of the question"),
    Target("gp_mob_sea_iros24", "Data-driven Force Observer for Human-Robot Interaction with Series Elastic Actuators using Gaussian Processes", doi="10.1109/iros58592.2024.10802608", role="neighbor", why_wave_a="GP learned observer (Hirche line)"),
    Target("casper_lsens26", "CatBoost-Driven Anomaly Detection in Industrial Robotic Arms Using CASPER Dataset", doi="10.1109/lsens.2026.3656499", role="dataset", why_wave_a="unknown public robot-arm AD dataset to identify"),
    # --- cross-robot / context / MTSAD (target: 15+) ---
    Target("couda_tii25", "CoUDA: Continual Unsupervised Domain Adaptation for Industrial Fault Diagnosis Under Dynamic Working Conditions", doi="10.1109/tii.2025.3538135", role="crossrobot", why_wave_a="continual condition-shift adaptation"),
    Target("tta_fd_tii25", "Online Adaptive Fault Diagnosis With Test-Time Domain Adaptation", doi="10.1109/tii.2024.3438240", role="crossrobot", why_wave_a="test-time adaptation for FD"),
    Target("mlfada_tim24", "Metric Learning-Based Few-Shot Adversarial Domain Adaptation: A Cross-Machine Diagnosis Method for Ball Screws of Industrial Robots", doi="10.1109/tim.2024.3403183", role="crossrobot", why_wave_a="few-shot cross-machine on robot components"),
    Target("robotjoint_da_tim22", "Intelligent Fault Diagnosis for Bearings of Industrial Robot Joints Under Varying Working Conditions Based on Deep Adversarial Domain Adaptation", doi="10.1109/tim.2022.3158996", role="crossrobot", why_wave_a="robot-joint FD under varying conditions"),
    Target("causal_dg_nn24", "Causal Disentanglement Domain Generalization for time-series signal fault diagnosis", doi="10.1016/j.neunet.2024.106099", role="crossrobot", why_wave_a="causal context-invariance mechanism"),
    Target("sim_da_tii22", "Simulation-Driven Domain Adaptation for Rolling Element Bearing Fault Diagnosis", doi="10.1109/tii.2021.3103412", role="crossrobot", why_wave_a="physics-sim-to-real FD transfer"),
    Target("openset_sfda_tii25", "Source-Free Domain Adaptation for Open-Set Cross-Domain Fault Diagnosis", doi="10.1109/tii.2025.3598445", role="crossrobot", why_wave_a="unknown-fault vs domain-shift separation"),
    Target("ruff_unifying_pieee21", "A Unifying Review of Deep and Shallow Anomaly Detection", doi="10.1109/jproc.2021.3052449", role="mtsad", why_wave_a="canonical AD theory anchor"),
    Target("pa_critique_aaai22", "Towards a Rigorous Evaluation of Time-Series Anomaly Detection", doi="10.1609/aaai.v36i7.20680", role="mtsad", why_wave_a="point-adjustment critique, protocol-defining"),
    Target("wu_keogh_tkde21", "Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress", doi="10.1109/tkde.2021.3112126", role="mtsad", why_wave_a="benchmark-flaw critique, protocol-defining"),
    Target("tranad_vldb22", "TranAD: Deep Transformer Networks for Anomaly Detection in Multivariate Time Series Data", doi="10.48550/arxiv.2201.07284", arxiv_id="2201.07284", role="mtsad", why_wave_a="recent-MTSAD baseline-slot candidate"),
    Target("dcdetector_kdd23", "DCdetector: Dual Attention Contrastive Representation Learning for Time Series Anomaly Detection", doi="10.1145/3580305.3599295", role="mtsad", why_wave_a="recent-MTSAD baseline-slot candidate"),
    Target("memto_neurips23", "MEMTO: Memory-guided Transformer for Multivariate Time Series Anomaly Detection", doi="10.48550/arxiv.2312.02530", arxiv_id="2312.02530", role="mtsad", why_wave_a="recent-MTSAD baseline-slot candidate"),
    Target("gdn_aaai21", "Graph Neural Network-Based Anomaly Detection in Multivariate Time Series", doi="10.1609/aaai.v35i5.16523", role="mtsad", why_wave_a="RoAD native-baseline family (GDN)"),
    Target("ncad_ijcai22", "Neural Contextual Anomaly Detection for Time Series", doi="10.24963/ijcai.2022/394", role="mtsad", why_wave_a="contextual AD formulation"),
    Target("multidomain_np_aei24", "Multidomain neural process model based on source attention for industrial robot anomaly detection", doi="10.1016/j.aei.2024.102910", role="crossrobot", why_wave_a="multi-domain robot AD"),
    Target("xdevice_dcgan_phm23", "Cross-Device Anomaly Detection of Health Status for Industrial Robot Joints Based on SWDCGAN-Deep CORAL", doi="10.1109/phm-hangzhou58797.2023.10482745", role="crossrobot", why_wave_a="cross-device robot-joint AD"),
    Target("mst_gat_if22", "MST-GAT: A multimodal spatial-temporal graph attention network for time series anomaly detection", doi="10.1016/j.inffus.2022.08.011", role="mtsad", why_wave_a="multimodal graph MTSAD"),
    Target("fgdae_ress23", "FGDAE: A new machinery anomaly detection method towards complex operating conditions", doi="10.1016/j.ress.2023.109319", role="mtsad", why_wave_a="condition-shift machinery AD"),
)


#: Wave B closes the lineage-quota gaps L500 left (L5 especially), adds the
#: curated classics reachable through author/institutional copies, and the
#: canonical recent-MTSAD candidates. Known-item additions not in the 680-row
#: screening set are recorded in screening_delta batch_18 for auditability.
WAVE_V2B: tuple[Target, ...] = (
    Target("approx_equiv_icml22", "Approximately Equivariant Networks for Imperfectly Symmetric Dynamics", doi="10.48550/arxiv.2201.11969", arxiv_id="2201.11969", role="l5", why_wave_a="approximate equivariance foundation (ICML22)"),
    Target("approx_equiv_gnn23", "Approximately Equivariant Graph Networks", role="l5", why_wave_a="approximate equivariance for graphs (NeurIPS23)"),
    Target("approx_equiv_np24", "Approximately Equivariant Neural Processes", role="l5", why_wave_a="approximate equivariance in meta-learning (NeurIPS24)"),
    Target("sym_structured_matrices24", "Symmetry-Based Structured Matrices for Efficient Approximately Equivariant Networks", role="l5", why_wave_a="efficient approximate equivariance"),
    Target("algebraic_priors25", "Algebraic Priors for Approximately Equivariant Networks", role="l5", why_wave_a="2025 approximate-equivariance theory"),
    Target("equact_se3_25", "EquAct: An SE(3)-Equivariant Multi-Task Transformer for Open-Loop Robotic Manipulation", role="l5", why_wave_a="where exact equivariance DOES work in manipulation"),
    Target("se3_kinematics_ral22", "Augmented Neural Network for Full Robot Kinematic Modelling in SE(3)", doi="10.1109/lra.2022.3180428", role="l5", why_wave_a="SE(3)-structured model learning"),
    Target("anomaly_transformer_iclr22", "Anomaly Transformer: Time Series Anomaly Detection with Association Discrepancy", arxiv_id="2110.02642", role="mtsad", why_wave_a="canonical recent MTSAD (ICLR22); known-item addition"),
    Target("usad_kdd20", "USAD: UnSupervised Anomaly Detection on Multivariate Time Series", doi="10.1145/3394486.3403392", role="mtsad", why_wave_a="classic-slot MTSAD baseline (KDD20)"),
    Target("idempotent_neurips25", "Multivariate Time Series Anomaly Detection with Idempotent Reconstruction", doi="10.52202/085713-5374", role="mtsad", why_wave_a="newest reconstruction family (NeurIPS25)"),
    Target("safepr_arxiv25", "SafePR: Unified Approach for Safe Parallel Robots by Contact Detection and Reaction with Redundancy Resolution", doi="10.48550/arxiv.2501.17773", arxiv_id="2501.17773", role="neighbor", why_wave_a="L6 Hannover PR line"),
    Target("pr_clamping_arxiv23", "Safe Collision and Clamping Reaction for Parallel Robots During Human-Robot Collaboration", doi="10.48550/arxiv.2308.09656", arxiv_id="2308.09656", role="neighbor", why_wave_a="collision-vs-clamping discrimination"),
    Target("mad_cnn_arxiv23", "Robust Collision Detection for Robots with Variable Stiffness Actuation by Using MAD-CNN: Modularized-Attention-Dilated Convolutional Neural Network", doi="10.48550/arxiv.2310.02573", arxiv_id="2310.02573", role="neighbor", why_wave_a="modular attention collision detection"),
    Target("kinetostatic_pr_icra23", "Towards Human-Robot Collaboration with Parallel Robots by Kinetostatic Analysis, Impedance Control and Contact Detection", doi="10.1109/icra48891.2023.10161217", role="neighbor", why_wave_a="PR kinetostatic contact detection"),
    Target("deluca_mattone_icra03", "Actuator failure detection and isolation using generalized momenta", role="classic", why_wave_a="the generalized-momentum FDI origin (ICRA03)"),
    Target("deluca_iros06", "Collision detection and safe reaction with the DLR-III lightweight manipulator arm", role="classic", why_wave_a="collision detection via MOB classic (IROS06)"),
    Target("federated_xrobot_plos25", "Federated fault diagnosis method for collaborative self-diagnosis and cross-robot peer diagnosis", doi="10.1371/journal.pone.0322484", role="crossrobot", why_wave_a="cross-robot peer diagnosis"),
    Target("lstm_contact_transfer_techrxiv25", "Learning-Based Contact Interpretation with LSTM Networks: A Transferable Skill for Robots", doi="10.36227/techrxiv.174742058.83011810/v1", role="crossrobot", why_wave_a="claimed cross-DoF transferable contact interpretation"),
    Target("clue_ai_access23", "CLUE-AI: A Convolutional Three-Stream Anomaly Identification Framework for Robot Manipulation", doi="10.1109/access.2023.3276297", role="l9", why_wave_a="multimodal manipulation anomaly identification"),
    Target("multimodal_hrc_sciprog21", "Comparison of deep learning-based methods in multimodal anomaly detection: A case study in human-robot collaboration", doi="10.1177/00368504211021192", role="l9", why_wave_a="multimodal robot AD comparison"),
    Target("sensorimotor_graph_iros21", "SENSORIMOTOR GRAPH: Action-Conditioned Graph Neural Network for Learning Robotic Soft Hand Dynamics", doi="10.1109/iros51168.2021.9636377", role="l4", why_wave_a="action-conditioned graph dynamics"),
    Target("pinn_cobot_ral23", "Physics-Informed Neural Network for Model Prediction and Dynamics Parameter Identification of Collaborative Robot Joints", doi="10.1109/lra.2023.3329620", role="l4", why_wave_a="PINN cobot joint dynamics"),
    Target("kalmannet_tsp22", "KalmanNet: Neural Network Aided Kalman Filtering for Partially Known Dynamics", doi="10.1109/tsp.2022.3158588", arxiv_id="2107.10043", role="l4", why_wave_a="hybrid structured estimation"),
    Target("active_inference_survey21", "Active Inference in Robotics and Artificial Agents: Survey and Challenges", doi="10.48550/arxiv.2112.01871", arxiv_id="2112.01871", role="l11", why_wave_a="active-inference robotics anchor"),
    Target("fd_ftc_review_arxiv24", "Review on Fault Diagnosis and Fault-Tolerant Control Scheme for Robotic Manipulators: Recent Advances in AI, Machine Learning, and Digital Twin", doi="10.48550/arxiv.2402.02980", role="review", why_wave_a="recent robot FD/FTC review"),
    Target("grounded_anomaly_jint21", "Endowing Robots with Longer-term Autonomy by Recovering from External Disturbances in Manipulation Through Grounded Anomaly Classification and Recovery Policies", doi="10.1007/s10846-021-01312-6", role="l7", why_wave_a="anomaly classification + recovery line"),
    Target("screwdriving_usecase_lnme21", "Detecting Faults During Automatic Screwdriving: A Dataset and Use Case of Anomaly Detection for Automatic Screwdriving", doi="10.1007/978-3-030-90700-6_25", role="dataset", why_wave_a="AURSAD-adjacent screwdriving AD use case"),
    Target("active_fdia_defence_26", "From Passive Monitoring to Active Defence: Resilient Control of Manipulators Under Cyberattacks", role="l11", why_wave_a="active defence vs stealthy FDIA"),
    Target("lie_ft_localization_25", "Fault-Tolerant Multi-Modal Localization of Multi-Robots on Matrix Lie Groups", role="l5", why_wave_a="Lie-group estimation with fault rejection"),
)

WAVES = {"a": WAVE_V2A, "b": WAVE_V2B}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="", help="comma-separated target ids")
    parser.add_argument("--wave", default="a", choices=sorted(WAVES))
    parser.add_argument("--extract-text", action="store_true")
    args = parser.parse_args(argv)

    if args.extract_text:
        for stem, pages, chars, text_sha in extract_text(OUT_DIR):
            print(f"  {stem:28s} pages={pages:3d} chars={chars:>8,}  text_sha256={text_sha[:16]}")
        return 0

    wanted = {s.strip() for s in args.only.split(",") if s.strip()}
    targets = [t for t in WAVES[args.wave] if not wanted or t.target_id in wanted]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    resolutions: list[Resolution] = []
    for target in targets:
        resolution = Resolution(target=target)
        resolve_openalex(resolution, session)
        resolve_unpaywall(resolution, session)
        resolve_semantic_scholar(resolution, session)
        resolve_openaire(resolution, session)
        resolve_arxiv(resolution, session)
        fetch_fulltext(resolution, session, OUT_DIR)
        resolution.canonical_citation_year = resolution.publication_year
        resolutions.append(resolution)
        print(
            f"{target.target_id:28s} {resolution.evidence_level:22s} "
            f"{resolution.access_route:20s} {resolution.local_bytes:>9,} B  {resolution.resolved_doi}",
            flush=True,
        )
        time.sleep(0.5)

    csv_path = MANIFEST_DIR / "fulltext_access_manifest_v2.csv"
    exists = csv_path.exists()
    with csv_path.open("a" if exists else "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        if not exists:
            writer.writeheader()
        for r in resolutions:
            writer.writerow({
                "target_id": r.target.target_id,
                "role": r.target.role,
                "resolved_title": r.resolved_title or r.target.title,
                "resolved_doi": r.resolved_doi,
                "venue": r.venue,
                "publication_status": r.publication_status,
                "publication_year": r.publication_year,
                "issue_publication_date": r.issue_publication_date,
                "canonical_citation_year": r.canonical_citation_year,
                "is_oa": r.is_oa,
                "oa_status": r.oa_status,
                "arxiv_id": r.arxiv_id,
                "evidence_level": r.evidence_level,
                "access_route": r.access_route,
                "open_fulltext_url": r.open_fulltext_url,
                "publisher_url": r.publisher_url,
                "local_pdf": r.local_pdf,
                "local_bytes": r.local_bytes,
                "local_sha256": r.local_sha256,
                "why_wave_a": r.target.why_wave_a,
                "notes": " | ".join(r.notes),
            })

    log = render_negative_search_log(resolutions, RUN_ID)
    (MANIFEST_DIR / "negative_search_log_v2.md").write_text(log, encoding="utf-8")

    levels: dict[str, int] = {}
    for r in resolutions:
        levels[r.evidence_level] = levels.get(r.evidence_level, 0) + 1
    print("levels:", dict(sorted(levels.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
