"""Phase D0: the feasibility cards, built only from probed evidence.

Every value below traces to a file under the run's ``d0_evidence/`` directory,
recorded by :mod:`certo_fdi_reset.datasets.probe`. Where the evidence does not
answer a question, the field stays ``UNKNOWN`` and the question is listed in
``open_verifications``: ``09_DATASET_FEASIBILITY_AND_DOWNLOAD_PROTOCOL.md`` §3
forbids filling a gap from the robot model, the paper's prose, or a simulator.

The physics grade is not a judgement call either -- it is derived by
:meth:`FeasibilityCard.grade` from the documented signals, and it is what decides
which candidate adapters are even permitted to run
(``13_CANDIDATE_MODEL_ADAPTER_PROTOCOL.md`` §2).

    python -m certo_fdi_reset.datasets.d0 --config configs/paper_reset.yaml
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field
from pathlib import Path

from ..config import load_config
from ..provenance import utc_stamp, write_manifest
from .feasibility import CARD_CSV_COLUMNS, FeasibilityCard, PhysicsGrade

D0_SCHEMA_VERSION = "1.0.0"


@dataclass
class DatasetD0:
    """One dataset's complete Phase D0 record."""

    card: FeasibilityCard
    role: str
    status: str
    canonical_paper: str = ""
    online_first_year: str = ""
    issue_year: str = ""
    canonical_citation_year: str = ""
    repo_commit: str = ""
    data_files: list[dict] = field(default_factory=list)
    license_notes: str = ""
    redistribution_note: str = ""
    signal_groups: list[dict] = field(default_factory=list)
    split_definition: str = ""
    normalization: str = ""
    leakage_risks: list[str] = field(default_factory=list)
    native_baseline: str = ""
    open_verifications: list[str] = field(default_factory=list)
    allowed_claims: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(f.get("size_bytes", 0) for f in self.data_files)


def build_cards() -> list[DatasetD0]:
    """Construct every card. Facts here are observations, not recollections."""
    return [_voraus_ad(), _road(), _aursad(), _ur5e(), _pyscrew(), _sarcos()]


def _voraus_ad() -> DatasetD0:
    card = FeasibilityCard(
        dataset_id="voraus_ad",
        official_url="https://github.com/vorausrobotik/voraus-ad-dataset",
        paper_doi="10.1109/TRO.2023.3332224",
        version="repo a91a86a (2023-11-09); data files re-published 2026-04-10",
        publication_date="2023-11-09",
        license_id="data: CC-BY-NC-SA-4.0; code: MIT",
        license_url="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        license_verified=True,
        redistribution_allowed=False,
        noncommercial_only=True,
        access_route="direct HTTPS download (media.vorausrobotik.com), no login",
        robot="voraus 6-axis collaborative robot",
        task="pick-and-place with a vacuum gripper",
        sampling_rate_hz=100.0,
        episode_unit="sample (one pick-and-place execution)",
        channel_count=137,
        documented_signals=[
            "joint_position_1..6", "joint_velocity_1..6", "motor_position_1..6",
            "motor_velocity_1..6", "motor_torque_1..6", "target_position_1..6",
            "target_velocity_1..6", "target_acceleration_1..6", "target_torque_1..6",
            "computed_torque_1..6", "computed_inertia_1..6", "torque_sensor_a_1..6",
            "torque_sensor_b_1..6", "motor_iq_1..6", "motor_id_1..6",
            "power_motor_el_1..6", "power_motor_mech_1..6", "power_load_mech_1..6",
            "motor_voltage_1..6", "supply_voltage_1..6", "brake_voltage_1..6",
            "robot_voltage", "robot_current", "io_current", "system_current",
            "time", "sample", "anomaly", "category", "setting/variant", "action", "active",
        ],
        has_joint_position=True,
        has_joint_velocity=True,
        has_joint_torque=True,
        has_commanded_torque=True,
        has_link_orientation=False,
        has_urdf_or_inertia=False,
        official_split=(
            "train = samples with variant == PRE_A (healthy only); test = all other variants. "
            "Verified on the downloaded 100 Hz file: 2122 episodes total, 948 train (0 anomalous), "
            "1174 test (755 anomalous, 419 normal)."
        ),
        label_semantics="anomaly flag + 12 anomaly categories + NORMAL_OPERATION + 77 variants + 15 actions",
        native_code_url="https://github.com/vorausrobotik/voraus-ad-dataset",
        native_code_commit="a91a86a642d23df58833b792a53de01edfd81abe",
        native_code_license="MIT",
    )
    card.files = [{"key": "voraus-ad-dataset-100hz.parquet"}, {"key": "voraus-ad-dataset-500hz.parquet"}]
    card.total_bytes = 1_115_942_833 + 5_328_361_187
    card.episode_unit = "sample (one pick-and-place execution); 2122 episodes in the 100 Hz file"
    card.grade()
    return DatasetD0(
        card=card,
        role="MANDATORY_1 — primary public anomaly benchmark",
        status="READY",
        canonical_paper="Brockmann, Rudolph, Rosenhahn, Wandt — The voraus-AD Dataset for Anomaly Detection in Robot Applications",
        online_first_year="2023",
        issue_year="2024",
        canonical_citation_year="2024",
        repo_commit="a91a86a642d23df58833b792a53de01edfd81abe",
        data_files=[
            {
                "key": "voraus-ad-dataset-100hz.parquet",
                "url": "https://media.vorausrobotik.com/voraus-ad-dataset-100hz.parquet",
                "size_bytes": 1_115_942_833,
                "etag": '"69d8ea42-4283efb1"',
                "last_modified": "Fri, 10 Apr 2026 12:17:06 GMT",
                "planned": True,
                "downloaded": True,
                "local_sha256": "c90ab1c78af52651b954d41787f7e89d750f0a128b57600b0e5ceec22621f704",
                "local_bytes": 1_115_942_833,
                "download_utc": "2026-08-18T14:45Z",
                "verified_rows": 2_321_690,
                "verified_columns": 137,
            },
            {
                "key": "voraus-ad-dataset-500hz.parquet",
                "url": "https://media.vorausrobotik.com/voraus-ad-dataset-500hz.parquet",
                "size_bytes": 5_328_361_187,
                "etag": '"69d8ea3a-13d9856e3"',
                "last_modified": "Fri, 10 Apr 2026 12:16:58 GMT",
                "planned": False,
            },
        ],
        license_notes="Repository LICENSE.txt is MIT (GitHub license API spdx_id=MIT). README states both data variants are CC BY-NC-SA 4.0.",
        redistribution_note="ShareAlike + NonCommercial: raw data must not enter git or any review package.",
        signal_groups=[
            {"group": "joint kinematics", "channels": "joint_position/velocity 1..6", "count": 12},
            {"group": "motor state", "channels": "motor_position/velocity/torque/iq/id 1..6", "count": 30},
            {"group": "commanded", "channels": "target_position/velocity/acceleration/torque 1..6", "count": 24},
            {"group": "model-derived", "channels": "computed_torque/computed_inertia 1..6", "count": 12},
            {"group": "torque sensing", "channels": "torque_sensor_a/b 1..6", "count": 12},
            {"group": "electrical", "channels": "power/voltage per axis + 4 global", "count": 40},
            {"group": "meta", "channels": "time, sample, anomaly, category, setting, action, active", "count": 7},
        ],
        split_definition="Official: variant PRE_A is the healthy training pool; every other variant is test. Episode unit = `sample`, so no window crosses the split.",
        normalization="StandardScaler fitted on training samples only; test transformed with the training statistics. Padding length = max training sample length; test truncated then padded.",
        leakage_risks=[
            "None found in the official loader: the scaler and the padding length are both derived from training only.",
            "frequency_divider downsampling is applied before splitting, which is order-independent and does not leak.",
        ],
        native_baseline="MVT-Flow (normalizing flow) — official repo, FrEIA @ 14484f1f875d5c4fedb9c4ff9d7eaa3f276bf150, torch 1.12.1, Python 3.9",
        open_verifications=[
            "Data files carry Last-Modified 2026-04-10, far later than the 2023/2024 paper. The 100 Hz file is now pinned locally by SHA256 c90ab1c7...f704; any future ETag change is a NEW data version and invalidates comparisons.",
            "Measured sample interval is 10.068 ms (99.3 Hz), not exactly the nominal 100 Hz; metrics reported per unit time must use the measured rate.",
            "Whether `computed_inertia_*` is a usable inertia quantity or a controller-internal scalar is unresolved; it is NOT link inertia and does not enable RNEA.",
        ],
        allowed_claims=[
            "healthy-only anomaly detection on real 6-axis manipulator data",
            "joint-space residual and chain-structured models using published joint position/velocity/torque",
        ],
        forbidden_claims=[
            "RNEA / full rigid-body dynamics residuals — no URDF, no link inertia tensors are published",
            "commercial use of the data (CC BY-NC-SA 4.0)",
        ],
        evidence=[
            "voraus_ad/repo.json", "voraus_ad/commits.json", "voraus_ad/license.json",
            "voraus_ad/readme.txt", "voraus_ad/dataset_module.txt", "voraus_ad/requirements.txt",
            "voraus_ad/data_100hz_headers.txt", "voraus_ad/data_500hz_headers.txt",
        ],
    )


def _road() -> DatasetD0:
    card = FeasibilityCard(
        dataset_id="road",
        official_url="https://gitlab.com/AlessioMascolini/roaddataset",
        paper_doi="10.1109/IECON51785.2023.10311726",
        version="git 8d3366984609 (2024-04-26)",
        publication_date="2023-10",
        license_id="UNKNOWN",
        license_url="",
        license_verified=False,
        redistribution_allowed=False,
        noncommercial_only=None,
        access_route="pip install git+https://gitlab.com/AlessioMascolini/roaddataset (data ships inside the package)",
        robot="KUKA LBR iiwa collaborative manipulator, 7 DoF, in a pilot production line; 7 IMU sensor ids 0..6 (identified from the VARADE paper p4 by the same authors)",
        task="production-line pick and place of ~20 g objects, with controlled anomalies: manual collisions (point), object-weight changes (collective), and trajectory speed reduced to 50% and 75% (collective, mixed with occasional collisions)",
        sampling_rate_hz=10.0,
        episode_unit="recording (list element per subset)",
        channel_count=87,
        documented_signals=[
            "robot action ID",
            "apparent power", "current", "frequency", "phase angle", "power",
            "power factor", "reactive power", "voltage",
            "per joint 1..7: x/y/z acceleration",
            "per joint 1..7: x/y/z angular velocity",
            "per joint 1..7: quaternion components 1-4",
            "per joint 1..7: temperature",
            "anomaly label",
        ],
        has_joint_position=False,
        has_joint_velocity=False,
        has_joint_torque=False,
        has_commanded_torque=False,
        has_link_orientation=True,
        has_urdf_or_inertia=False,
        official_split=(
            "Five named subsets. Verified recording counts: training=9, collision=2, control=1, "
            "weight=1, velocity=2 -- 15 recordings in total. No further official split is published."
        ),
        label_semantics=(
            "The label is a COUNT of co-occurring anomalies at each timestep, not a class id: 0, 1 or 2 "
            "(RoAD paper §IV). Verified per subset: training has 86 columns (no label at all); "
            "collision 0/1 with 1.52% anomalous rows; control all-0 (a healthy non-training subset); "
            "weight all-1; velocity carries 1 AND 2, where 2 means a collision occurred on top of the "
            "underlying speed-change anomaly -- so velocity is a MIXED point+collective scenario, not "
            "a second anomaly class."
        ),
        native_code_url="https://gitlab.com/AlessioMascolini/varade",
        native_code_commit="43f9b3c8b3f4c842097adc10270e364e2935663c",
        native_code_license="UNKNOWN — the varade repository ships no LICENSE file either",
    )
    card.grade()
    return DatasetD0(
        card=card,
        role="MANDATORY_2 — cross-context benchmark",
        status="READY_WITH_LICENSE_RESTRICTION",
        canonical_paper="Mascolini et al. — Robotic Arm Dataset (RoAD)",
        online_first_year="2023",
        issue_year="2023",
        canonical_citation_year="2023",
        repo_commit="8d3366984609",
        data_files=[
            {"key": "RoADDataset/data/training.pkl", "size_bytes": 160_849_424, "blob_sha256": "767c9e40dfe554eb"},
            {"key": "RoADDataset/data/control.pkl", "size_bytes": 51_851_471, "blob_sha256": "6f512bac1074ea5e"},
            {"key": "RoADDataset/data/collision.pkl", "size_bytes": 34_208_611, "blob_sha256": "607719540b925e6b"},
            {"key": "RoADDataset/data/velocity.pkl", "size_bytes": 28_910_659, "blob_sha256": "3c68ad285f1c3d4c"},
            {"key": "RoADDataset/data/weight.pkl", "size_bytes": 12_952_029, "blob_sha256": "e23994710899cbc8"},
            {"key": "RoADDataset/data/columns.pkl", "size_bytes": 1_673, "blob_sha256": "362669c7ea2ccb2b"},
        ],
        license_notes=(
            "No LICENSE/COPYING file exists: the GitLab files API returns 404 for LICENSE and the project "
            "license field is null. setup.py declares license='MIT' as package metadata only, with no license "
            "text distributed and no separate statement about the data. Declared-but-unaccompanied."
        ),
        redistribution_note="Local research analysis proceeds provisionally; redistribution of raw data is forbidden, in git and in review packages alike.",
        signal_groups=[
            {"group": "action", "channels": "robot action ID in [0,30]", "count": 1},
            {"group": "whole-system electrical", "channels": "apparent power … voltage (Eastron SDM230 single-phase meter)", "count": 8},
            {"group": "per-joint IMU linear", "channels": "3-axis acceleration × 7 joints", "count": 21},
            {"group": "per-joint IMU angular", "channels": "3-axis angular velocity × 7 joints", "count": 21},
            {"group": "per-joint orientation", "channels": "quaternion (4) × 7 joints", "count": 28},
            {"group": "per-joint thermal", "channels": "temperature × 7 joints", "count": 7},
            {"group": "label", "channels": "anomaly", "count": 1},
        ],
        split_definition="Subsets only; any train/test split must be constructed and declared by us, at recording granularity.",
        normalization="Official loader default normalize=True: MinMaxScaler fitted on the concatenated training subset, applied to columns 0:86 of every subset; column 86 is the label and is left untouched.",
        leakage_risks=[
            "The official scaler is fitted on training only, so the default path does not leak.",
            "No official validation split exists: hyperparameters must be chosen on a held-out slice of training recordings, never on the anomaly subsets.",
            "SEVERE STATISTICAL LIMIT: with 9 training and 6 non-training recordings, an episode-level cluster bootstrap (12_CROSS_DATASET_FAIRNESS_AND_METRICS) has almost no power, and the candidate-survival rule's >=2 concordant contexts cannot be met at recording granularity on this dataset alone.",
        ],
        native_baseline=(
            "VARADE (Mascolini et al., DAC 2024, doi 10.1145/3649329.3655691), code at "
            "gitlab.com/AlessioMascolini/varade @ 43f9b3c8. Ships VAAR.py, Transformer.py, "
            "autoencoder.py, BERTTrainer.py, positionalEncoding.py, main.py, trained checkpoints "
            "(VAAR, AE, ARLSTM, BERT, GBRT, IsolationForest, KNN), and a bundled copy of only the "
            "training and collision subsets. Reported result: AUC-ROC 0.84 on an 82-minute collision "
            "recording containing 125 human-induced collisions (VARADE p5). SCOPE LIMIT: the native "
            "baseline covers the COLLISION condition only -- weight, velocity and control have no "
            "native baseline, so any number we produce there is our own policy baseline, not a "
            "reproduction."
        ),
        open_verifications=[
            "RESOLVED, and it corrects an earlier reading: the IMUs RECORD at 200 Hz, but the RoAD paper §IV states the recordings were RESAMPLED TO 10 Hz before publication, so the released arrays are 10 Hz. Verified numerically: at 10 Hz the training subset is 389.7 min and the collision subset 81.9 min, matching the 390 min and 82 min that the VARADE paper independently reports for the same recordings. The robot's own controller interface is limited to 5 Hz, which is why IMUs were added at all -- nothing here comes from the robot controller.",
            "PARTIALLY RESOLVED via the RoAD paper §IV and VARADE p4, which agree: the quaternions are not raw IMU output -- three Euler angles per node were converted to unit quaternions because the [-180,+180] deg range wraps. The component ORDER (w-first vs w-last) is still undocumented and must be settled numerically before any orientation-aware feature is built.",
            "Frame convention, IMU mounting, and joint/link assignment per channel block are undocumented.",
            "Quaternion sign continuity across a recording is unverified.",
            "Inter-joint time synchronisation is unverified.",
            "CONFOUND (VARADE p4): the energy meter monitors the robot AND the industrial PC on the same phase, so the 8 power channels carry PC load. A detector can score well by learning PC activity rather than robot state; power channels must be ablated separately.",
            "Units for acceleration, angular velocity, and temperature are unstated.",
            "RESOLVED: the training subset genuinely has 86 columns. The official loader still slices [:, 86:] for it, which yields an empty (N,0) array, so training comes back with 86 columns while every other subset has 87. Any downstream code that assumes a uniform width breaks silently.",
            "Quaternion channels are named sensor_idK_q1..q4; whether q1 is the scalar part is still undocumented.",
        ],
        allowed_claims=[
            "orientation/inertial-aware chain model over published IMU quaternion, angular velocity, acceleration, temperature and joint-chain topology",
        ],
        forbidden_claims=[
            "RNEA model",
            "SE(3) rigid-body dynamics model",
            "physical wrench model",
            "any use of joint angle, joint torque, or encoder signals — none are published",
        ],
        evidence=[
            "road/repo.json", "road/tree.json", "road/commits.json", "road/readme.txt",
            "road/functions.txt", "road/setup.txt", "road/license_probe.http404.txt",
            "road/blob_training.json", "road/blob_collision.json", "road/blob_control.json",
            "road/blob_weight.json", "road/blob_velocity.json", "road/blob_columns.json",
            "01_frozen_sources/public_baseline_repos/roaddataset @ 8d3366984609d952ae933e3ce6335ad29c7838be",
            "01_frozen_sources/public_baseline_repos/varade @ 43f9b3c8b3f4c842097adc10270e364e2935663c",
        ],
    )


def _aursad() -> DatasetD0:
    card = FeasibilityCard(
        dataset_id="aursad",
        official_url="https://zenodo.org/records/4559556",
        paper_doi="10.48550/arXiv.2102.01409",
        version="1.1 (concept DOI 10.5281/zenodo.4487072; v1.0 = record 4487073); AURSAD.h5 md5 08e4706cf15144761a12cb86bd071d72 verified locally",
        publication_date="2021-02-01",
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        license_verified=True,
        redistribution_allowed=True,
        noncommercial_only=False,
        access_route="Zenodo REST API (web UI 403s from this host; the API does not)",
        robot="Universal Robots UR3e with an OnRobot screwdriver",
        task="automated screwdriving",
        sampling_rate_hz=100.0,
        episode_unit="sample (one screwdriving operation)",
        channel_count=134,
        documented_signals=[
            "timestamp",
            "actual_q_0..5 (measured joint position)",
            "actual_qd_0..5 (measured joint velocity)",
            "actual_current_0..5 (measured joint current)",
            "target_q_0..5, target_qd_0..5, target_qdd_0..5 (commanded kinematics)",
            "target_moment_0..5 (commanded joint moment)",
            "target_current_0..5",
            "joint_control_output_0..5",
            "actual_TCP_pose/speed/force_0..5 (controller-estimated TCP wrench)",
            "target_TCP_pose/speed_0..5",
            "joint_temperatures_0..5",
            "actual_joint_voltage_0..5",
            "actual_momentum, actual_execution_time, speed_scaling, target_speed_fraction",
            "actual_tool_accelerometer_0..2",
            "actual_main_voltage, actual_robot_voltage, actual_robot_current",
            "robot_mode, joint_mode_0..5, safety_mode, runtime_state",
            "digital/int/double registers",
            "label, sample_nr",
        ],
        has_joint_position=True,
        has_joint_velocity=True,
        has_joint_torque=False,
        has_commanded_torque=True,
        has_link_orientation=False,
        has_urdf_or_inertia=False,
        official_split="No official split is published; the loader builds train/test itself.",
        label_semantics=(
            "Verified from the file: 4094 samples = 2045 labelled 0-4 plus 2049 labelled 5. "
            "0 normal 1420, 1 damaged screw 221, 2 extra assembly component 183, 3 missing screw 218, "
            "4 damaged thread 3. Labels are constant within a sample, so the episode label is unambiguous."
        ),
        native_code_url="https://github.com/CptPirx/AURSAD",
        native_code_commit="c4a2b683b2f459757f9bd50fc518f7039829ab7a",
        native_code_license="MIT",
    )
    card.grade()
    return DatasetD0(
        card=card,
        role="MANDATORY_3 — industrial process anomaly benchmark",
        status="READY",
        canonical_paper="Rytter Rakauskas — AURSAD: Universal Robot Screwdriving Anomaly Detection Dataset",
        online_first_year="2021",
        issue_year="2021",
        canonical_citation_year="2021",
        repo_commit="",
        data_files=[
            {"key": "AURSAD.h5", "record": "4487073 (v1.0) and 4559556 (v1.1)", "size_bytes": 6_417_816_949, "md5": "08e4706cf15144761a12cb86bd071d72", "planned": True},
            {"key": "AURSAD.pkl", "record": "4559556 (v1.1)", "size_bytes": 6_417_804_117, "md5": "cd9065a822867b6bbbb3f4cce8107b0e", "planned": False},
        ],
        license_notes="Zenodo metadata license id cc-by-4.0, access_right open, on both records. Official loader CptPirx/AURSAD is MIT; CptPirx/AURSAD-source carries no license.",
        redistribution_note="CC-BY-4.0 permits redistribution with attribution, but raw data still stays out of git and out of review packages on size grounds.",
        signal_groups=[
            {"group": "measured joint state", "channels": "actual_q/qd/current 0..5", "count": 18},
            {"group": "commanded joint state", "channels": "target_q/qd/qdd/moment/current 0..5", "count": 30},
            {"group": "joint control", "channels": "joint_control_output 0..5, joint_mode 0..5", "count": 12},
            {"group": "TCP", "channels": "actual/target TCP pose, speed, force", "count": 30},
            {"group": "thermal/electrical", "channels": "joint_temperatures, joint_voltage, robot voltage/current", "count": 15},
            {"group": "tool", "channels": "actual_tool_accelerometer 0..2", "count": 3},
            {"group": "status/registers", "channels": "robot_mode, safety_mode, runtime_state, registers", "count": 24},
            {"group": "meta", "channels": "timestamp, label, sample_nr", "count": 3},
        ],
        split_definition="No official split; ours must be episode-safe at sample_nr granularity, with per-class counts reported because damaged-thread has n=3.",
        normalization="Loader offers optional z-score standardisation; must be fitted on training only.",
        leakage_risks=[
            "The loader's sliding-window 'prediction mode' labels a window by the NEXT sample's class, which mixes horizons; the labelling mode must be frozen before any result.",
            "CRITICAL LEAKAGE RISK (AURSAD paper p15): of the 134 columns, several are auxiliary features 'intentionally added during data collection to allow for easier data manipulation and labeling' and are 'not representative of the actual data that the UR or screwdriver provide'. The paper's recommended feature count is 125. Training on all 134 can leak the label through its own labelling helpers, so the 125-feature set must be fixed before any AURSAD result.",
            "Damaged-thread has n=3 samples: any split that puts all three on one side makes that class unlearnable or untestable. Per-class counts must be reported.",
        ],
        native_baseline=(
            "The paper's own benchmarks are SUPERVISED multi-class classifiers, not healthy-only "
            "anomaly detection: LSTM F1 4.79% on raw data (it collapsed to a single class), TABL "
            "43.11%, and after PCA 44.68% / 71.02% (p19). A faithful native reproduction here "
            "reproduces a supervised classifier; a healthy-only detector is a DIFFERENT TASK on the "
            "same data and may not be compared to these numbers as if it were the same benchmark."
        ),
        open_verifications=[
            "RESOLVED: 134 columns confirmed in the HDF5 (block0 7 uint8, block1 111 float64, block2 15 int64, block3 1 int32), 6,249,074 rows, timestamp dt exactly 0.01 s = 100.00 Hz.",
            "RESOLVED: measured joint position and velocity ARE present (actual_q, actual_qd), but there is NO measured joint torque -- only target_moment (commanded) and actual_current. Grade is therefore P2, not P3.",
            "RESOLVED: the file contains 2045 samples with labels 0-4, matching the official README; the arXiv abstract's 2042 is superseded.",
            "A public UR3e URDF exists outside this dataset. Importing it to reach P3 would supply a missing quantity from the robot model, which 09_DATASET_FEASIBILITY §3 forbids: the grade stays P2 and rnea_gmo_public stays unavailable.",
            "Sample lengths run from 13 to 3795 rows (median 1540); the 13-row samples must be inspected before windowing, since they are shorter than any reasonable window.",
            "actual_TCP_force is the controller's own estimate, not an external force/torque sensor, and must not be presented as ground-truth contact wrench.",
        ],
        allowed_claims=[
            "process anomaly detection on a real UR3e screwdriving cell",
            "joint-space residual and chain models over published actual_q/actual_qd and commanded target_moment",
        ],
        forbidden_claims=[
            "calling a screwdriving process anomaly a manipulator body fault",
            "comparing a healthy-only anomaly score against the paper's supervised F1 numbers as though they measured the same task",
            "any physics-residual claim before the schema audit resolves what is actually recorded",
        ],
        evidence=[
            "aursad/zenodo_4487073.json", "aursad/zenodo_4559556.json", "aursad/arxiv.txt",
            "aursad/code_repo.json", "aursad/code_readme.txt", "aursad/code_source_repo.json",
        ],
    )


def _ur5e() -> DatasetD0:
    card = FeasibilityCard(
        dataset_id="ur5e_graabaek",
        official_url="https://zenodo.org/records/5849300",
        # The dataset DOI and the paper DOI are different objects. The dataset README
        # (written 2022) calls the paper "under review"; it was published the next
        # year, so that note is stale and the paper is citable.
        paper_doi="10.1109/ACCESS.2023.3289068",
        version="record 5849300 (concept 10.5281/zenodo.5849299), dataset DOI 10.5281/zenodo.5849300",
        publication_date="2022-01-24",
        license_id="CC-BY-NC-4.0",
        license_url="https://creativecommons.org/licenses/by-nc/4.0/",
        license_verified=True,
        redistribution_allowed=False,
        noncommercial_only=True,
        access_route="Zenodo REST API",
        robot=(
            "Universal Robots UR5e (UR software 5.9.1) with a Robotiq 2F-85 gripper on the "
            "TCP, on a 1.2 x 0.8 m Siegmund table with an Intel RealSense D435i overhead; a "
            "digital button on digital input pin 5 marks anomaly onset"
        ),
        task=(
            "stochastic pick-and-place between three marked squares with a metal cylinder "
            "(2.0 kg default, 4 masses available); the branch via square 2 fires 16% of the "
            "time and the direct square 1 -> 3 path 84%, and square 3's place target is "
            "randomised in a 20 x 20 cm box to imitate a camera pose estimate"
        ),
        sampling_rate_hz=100.0,
        episode_unit="program run (a full application execution); replications per condition",
        channel_count=121,
        documented_signals=[
            "timestamp, actual_execution_time",
            "target_q/qd/qdd (6 each) — commanded joint position, velocity, ACCELERATION",
            "target_current, target_moment (6 each) — COMMANDED joint current and joint torque",
            "target_TCP_pose, target_TCP_speed (6 each)",
            "actual_q, actual_qd (6 each) — measured joint position and velocity",
            "actual_current (6) — measured motor current; there is NO measured joint torque channel",
            "joint_temperatures (6)",
            "actual_TCP_pose, actual_TCP_speed, actual_TCP_force (6 each) — measured TCP wrench",
            "actual_tool_accelerometer (3)",
            "actual_momentum (1) — the controller's own generalised-momentum scalar",
            "actual_main_voltage, actual_robot_voltage, actual_robot_current, actual_joint_voltage (6)",
            "joint_control_output (6)",
            "robot_mode, joint_mode (6), safety_mode, speed_scaling, target_speed_fraction, runtime_state, script_control_line",
            "actual_digital_input_bits, actual_digital_output_bits",
            "output_double_register_20 = loop index, output_double_register_21 = code line number",
        ],
        has_joint_position=True,
        has_joint_velocity=True,
        # No measured joint torque exists. target_moment is the COMMANDED torque and
        # actual_current is a motor-current proxy; conflating either with a measured
        # joint torque would manufacture an observation the dataset does not contain.
        has_joint_torque=False,
        has_commanded_torque=True,
        # actual_TCP_pose carries end-effector orientation as a rotation vector, but
        # there is no per-link orientation anywhere -- unlike RoAD's per-joint IMUs.
        has_link_orientation=False,
        has_urdf_or_inertia=False,
        official_split=(
            "A partial split IS published, as data/stochastic_PnP/anomaly_dict.pkl: a dict "
            "of the 8 anomaly conditions, each listing exactly 10 run names under a single "
            "'test' key. There is NO 'validation' key and no healthy split, so the healthy "
            "train/validation division is the user's to make. Verified file inventory: "
            "normal 508 runs, normal_branch 102, normal_extra_wait 35 (645 healthy runs, "
            "no label files), plus 10 runs x 8 anomaly conditions each with a paired "
            "per-sample _label.npy, all under <condition>/test/ -- 725 CSVs total."
        ),
        label_semantics=(
            "Per-sample labels in a float64 .npy aligned 1:1 with the CSV data rows "
            "(verified: 2279 rows, 2279 labels). Values are 0 or 32 in stochastic_PnP and "
            "0 or 1 in hyp -- 32 is a flat 'anomalous' marker, NOT a type code: every one "
            "of the 8 conditions uses the same 32, so the anomaly type is carried by the "
            "directory name only. Onset is marked live by the operator's digital-input "
            "button and then CORRECTED after collection against the button state and "
            "status registers, so the labels are curated rather than automatic. Each "
            "anomaly has its own written start/end rule."
        ),
        native_code_url="DataLoadingExample.py, shipped inside data.zip (requires ur-rtde)",
        native_code_license="UNKNOWN — no license file accompanies the loader script",
    )
    card.grade()
    return DatasetD0(
        card=card,
        role="SUPPLEMENTARY — independent robot anomaly replication",
        status="READY",
        canonical_paper=(
            "Graabæk, Ancker, Fugl & Christensen — An Experimental Comparison of Anomaly "
            "Detection Methods for Collaborative Robot Manipulators, IEEE Access 11 (2023), "
            "doi:10.1109/ACCESS.2023.3289068; preprint TechRxiv 10.36227/techrxiv.19006643 "
            "(v1/v2 2022, v3 2023)"
        ),
        online_first_year="2022",
        issue_year="2023",
        canonical_citation_year="2023",
        data_files=[
            {"key": "data.zip", "size_bytes": 2_584_585_052, "md5": "7b69a1794ee1bca152fbf32ec627747e", "planned": True, "downloaded": True, "md5_verified": True, "verified_contents": "1685 entries, 725 CSVs at 121 columns, 80 label .npy, extracted size 7,326,813,579 B"},
            {"key": "ExperimentalDescription.pdf", "size_bytes": 1_148_708, "md5": "c24f5f6d09e9aa89f3aa3f4300a76932", "planned": True, "downloaded": True, "md5_verified": True},
            {"key": "README.md", "size_bytes": 2_017, "md5": "f519ec2525a9a510f21fef24db6311c3", "planned": True, "downloaded": True, "md5_verified": True},
        ],
        license_notes="Zenodo license id cc-by-nc-4.0: non-commercial only, and redistribution is not exercised.",
        redistribution_note="NonCommercial: excluded from every review package.",
        split_definition=(
            "None published. A split must be built per program run, never per sample: "
            "consecutive samples inside one run are 10 ms apart and an anomaly spans a "
            "contiguous stretch of them."
        ),
        normalization="none published",
        native_baseline="the paper's own comparison of anomaly detection methods (IEEE Access 2023)",
        leakage_risks=[
            "the archive holds TWO datasets -- stochastic_pnp (the full application) and "
            "hyp (the paper's hypothesis set). They are different experiments and must not "
            "be pooled.",
            "600 normal replications vs 10 per anomaly: a per-sample split would let the "
            "same program run appear on both sides.",
            "status register 21 encodes the program node, i.e. exactly which scripted "
            "motion is running. It is a legitimate context variable but a model given it "
            "directly can read the wait-time anomaly off the schedule instead of the "
            "dynamics.",
        ],
        open_verifications=[
            "RESOLVED: the logged channel set is now read directly out of the archive. "
            "logging/record_configuration.xml is the RTDE recipe and the CSV header "
            "confirms it -- 121 space-delimited columns. The sampling rate is verified "
            "numerically too: median dt = 0.010000 s over normal_r0, i.e. exactly 100 Hz.",
            "RESOLVED: 'force_stop' in the archive IS the description PDF's 'Raised object' "
            "anomaly -- the PDF describes a 22 mm or 48 mm slab at a pick/place location "
            "and the in-archive README describes a 22 mm or 48 mm plate making the robot "
            "pick at the wrong height. Two independent confirmations: the mechanism text, "
            "and the contamination rate (14.2% measured over the 10 released runs vs 14.04% "
            "in the PDF's table). The released tree has no 'raised_object' directory; it is "
            "a rename, not a missing condition.",
            "DISCREPANCY, unresolved: the description PDF's table reports 600 normal "
            "replications, while the archive holds 645 healthy runs (508 + 102 + 35). "
            "Per-anomaly contamination agrees closely with the PDF everywhere (outside_box "
            "32.1 vs 32.08, change_weight 34.4 vs 33.32, tcp_wrench 15.5 vs 15.00, "
            "scale_speed 24.2 vs 22.71, long_wait 11.3 vs 11.67, push 9.4 vs 8.64, "
            "drop_object 25.2 vs 22.92), so the release is consistent with the paper on "
            "the anomalies and differs only in the healthy count.",
            "No URDF and no inertial parameters are distributed. A UR5e model is publicly "
            "available elsewhere, but 09_DATASET_FEASIBILITY 6.4 forbids supplying a "
            "missing physical quantity from the robot MODEL, so this dataset cannot be "
            "graded P3 and rnea_gmo_public stays NOT_APPLICABLE here.",
            "The three healthy variants (normal, normal_branch, normal_extra_wait) are "
            "different program behaviours, not replicates; whether they may be pooled as "
            "one healthy distribution is a modelling decision, not a dataset fact.",
        ],
        allowed_claims=[
            "an independent second collaborative-manipulator anomaly benchmark with a "
            "documented, human-marked and then hand-corrected label protocol",
            "the richest P2 signal set in this registry: it is the only dataset here that "
            "publishes commanded joint torque (target_moment), a measured TCP wrench "
            "(actual_TCP_force) and the controller's own generalised momentum "
            "(actual_momentum) alongside q and qd -- i.e. the ingredients of a "
            "momentum-observer-style residual WITHOUT needing an inertial model",
        ],
        forbidden_claims=[
            "commercial use",
            "any per-channel schema claim before the channel list is read out of data.zip",
            "treating the 8 conditions as one homogeneous anomaly class -- long wait and "
            "outside box are scheduling/planning faults, while push and TCP wrench are "
            "contact events, and only the latter are comparable to a collision benchmark",
        ],
        evidence=[
            "ur5e_graabaek/zenodo_5849300.json",
            "ur5e_graabaek/zenodo_concept.json",
            "ur5e_graabaek/crossref_paper.json",
            "03_data/public/ur5e_graabaek/README.md (md5-verified)",
            "03_data/public/ur5e_graabaek/ExperimentalDescription.pdf (md5-verified; 9 pages read)",
            "03_data/public/ur5e_graabaek/data.zip (md5 7b69a1794ee1bca152fbf32ec627747e verified against the Zenodo record; unzip -t clean; RTDE recipe, CSV header, label .npy, anomaly_dict.pkl and timestamps all read directly)",
        ],
    )


def _pyscrew() -> DatasetD0:
    card = FeasibilityCard(
        dataset_id="pyscrew",
        official_url="https://github.com/nikolaiwest/pyscrew",
        paper_doi="10.48550/arXiv.2505.11925",
        version="v1.2.3 = Zenodo record 16031381 (concept 10.5281/zenodo.14729547), published 2025-07-17; s03 archive md5 a21fea4da2bfe0138d582584ddfe27f5 verified locally against the record",
        publication_date="2025-07-17",
        license_id="CC-BY-4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        license_verified=True,
        redistribution_allowed=True,
        noncommercial_only=False,
        access_route="Zenodo record 16031381 (v1.2.3); the pyscrew package wraps the same archives",
        robot="automatic screwdriving station (Deprag CS351 controller, Delta PT 40x12 screws into thermoplastic housings) -- NO manipulator and no joint instrumentation",
        task="screw driving across six experimental scenarios; s03 audited in full",
        sampling_rate_hz=833.33,
        episode_unit="screw driving operation = 4 tightening steps (Finding, Thread forming, Pre-tightening, Final tightening at 1.4 Nm), each a variable-length series",
        channel_count=6,
        documented_signals=[
            "angle values (deg)",
            "torque values (Nm)",
            "gradient values",
            "torqueRed values",
            "angleRed values",
            "time values (s, restarting at 0 within each of the 4 steps)",
        ],
        has_joint_position=False,
        has_joint_velocity=False,
        has_joint_torque=False,
        has_link_orientation=False,
        has_urdf_or_inertia=False,
        official_split=(
            "No train/test split is published. s03 verified from the archive: 1700 "
            "operations over 26 classes and 869 unique workpieces."
        ),
        label_semantics=(
            "Three parallel label columns in labels.csv, verified on s03: "
            "workpiece_result is the station's own OK/NOK verdict (1067 OK / 633 NOK); "
            "class_value is the 26-way experimental condition; scenario_condition is "
            "normal/faulty by DESIGN INTENT (500 normal / 1200 faulty) and does NOT "
            "agree with workpiece_result -- an intentionally faulty setup often still "
            "produces an OK screw (e.g. 201_adhesive-thread is 43 OK / 7 NOK). Which "
            "column is 'the' anomaly label is therefore a modelling choice that must be "
            "declared, not an intrinsic property of the data."
        ),
        native_code_url="https://github.com/nikolaiwest/pyscrew",
        native_code_license="CC-BY-4.0",
    )
    card.grade()
    return DatasetD0(
        card=card,
        role="OPTIONAL_LARGE_SCALE — process generalization only",
        status="AVAILABLE_LOW_PRIORITY",
        canonical_paper="West et al. — PyScrew / industrial screw driving dataset collection",
        online_first_year="2025",
        issue_year="2025",
        canonical_citation_year="2025",
        data_files=[
            {"key": "s01_variations-in-thread-degradation.zip", "size_bytes": 29_004_994, "md5": "d125657a4b6d7ea0e4a985a4727ebb78", "planned": False},
            {"key": "s02_variations-in-surface-friction.zip", "size_bytes": 83_946_972, "md5": "0bc948a6e8c6e83f72dbe36973131558", "planned": False},
            {
                "key": "s03_variations-in-assembly-conditions-1.zip",
                "size_bytes": 12_588_378,
                "md5": "a21fea4da2bfe0138d582584ddfe27f5",
                "planned": True,
                "downloaded": True,
                "md5_verified": True,
                "verified_contents": "1700 json/ operations + labels.csv (1700 rows) + README.md; unzip -t clean",
            },
            {"key": "s04_variations-in-assembly-conditions-2.zip", "size_bytes": 61_107_763, "md5": "7f580205863743c2b083cbeebfa61117", "planned": False},
            {"key": "s05_variations-in-upper-workpiece-fabrication.zip", "size_bytes": 26_702_174, "md5": "eab215fe08d38c30ca0366a0665c4bbd", "planned": False},
            {"key": "s06_variations-in-lower-workpiece-fabrication.zip", "size_bytes": 83_080_694, "md5": "ddb668b1e4db64aeb910d07f3ee4e010", "planned": False},
        ],
        license_notes="Zenodo record license cc-by-4.0; the GitHub repository itself is licensed CC-BY-4.0.",
        redistribution_note="Attribution required; not redistributed here.",
        split_definition=(
            "MUST be grouped by workpiece_id, not by operation. Verified on s03: 1700 "
            "operations share only 869 workpieces, 785 workpieces appear more than once "
            "and one carries 11 operations, so an operation-level split puts the same "
            "physical workpiece on both sides."
        ),
        normalization="package offers padding/truncation to a target length and duplicate/missing handling; the archive itself is raw (README: no preprocessing)",
        native_baseline="none frozen (the s03 README states no paper is planned for s03; cite the Zenodo record)",
        open_verifications=[
            "Only s03 is audited. s01, s02, s04-s06 are inventoried by md5 and size but "
            "their schemas are unread, and s03's own README shows the scenarios are not "
            "independent -- see the leakage note.",
            "Missing values are 3.65% per the s03 README; the mechanism and per-channel "
            "distribution are not audited.",
        ],
        leakage_risks=[
            "workpiece reuse WITHIN a scenario: 785 of 869 s03 workpieces carry more than "
            "one operation (max 11), and workpiece_usage counts prior screw runs on the "
            "same piece, so the split unit must be workpiece_id.",
            "workpiece reuse ACROSS scenarios: 9 of s03's 26 classes are not new "
            "recordings at all. Counted from labels.csv: 003_control-group-from-s01 (200 "
            "ops) is copied from s01, and 004_control-group-from-s02 (100) plus 601..607 "
            "(400) are copied from s02 -- 700 of 1700 operations, 41.2%, so only 1000 "
            "were originally recorded for s03. Pooling scenarios would put identical "
            "operations on both sides of a split.",
            "left/right position: a workpiece takes one screw per location, so its two "
            "operations are near-duplicates of each other.",
        ],
        allowed_claims=["process-level anomaly detection generalization across screwdriving scenarios"],
        forbidden_claims=[
            "describing a screwdriving process anomaly as a robot-arm body fault",
            "any joint-space or physics-residual claim — no manipulator signals exist here",
            "pooling two or more scenarios without removing the copied control/condition "
            "groups first",
        ],
        evidence=[
            "pyscrew/repo.json", "pyscrew/readme.txt", "pyscrew/zenodo_14769379.json",
            "pyscrew/zenodo_concept.json", "pyscrew/zenodo_16031381.json", "pyscrew/arxiv.txt",
            "03_data/public/pyscrew/s03_variations-in-assembly-conditions-1.zip (md5-verified; README, labels.csv and json/ read directly)",
        ],
    )


def _sarcos() -> DatasetD0:
    card = FeasibilityCard(
        dataset_id="sarcos",
        official_url="http://gaussianprocess.org/gpml/data/",
        paper_doi="",
        version="classic distribution (sarcos_inv.mat / sarcos_inv_test.mat)",
        publication_date="",
        license_id="UNKNOWN",
        license_verified=False,
        redistribution_allowed=False,
        noncommercial_only=None,
        access_route="direct HTTP download from gaussianprocess.org",
        robot="SARCOS 7-DoF anthropomorphic arm",
        task="inverse dynamics regression (healthy operation only)",
        sampling_rate_hz=None,
        episode_unit="sample row",
        channel_count=28,
        documented_signals=["7 joint positions", "7 joint velocities", "7 joint accelerations", "7 joint torques"],
        has_joint_position=True,
        has_joint_velocity=True,
        has_joint_torque=True,
        has_link_orientation=False,
        has_urdf_or_inertia=False,
        official_split=(
            "published train / test .mat files, verified by loading them: sarcos_inv "
            "(44484, 28) and sarcos_inv_test (4449, 28), float64, no NaN or inf, one "
            "MATLAB 5.0 variable per file and no other keys."
        ),
        label_semantics="regression targets are torques; there are NO anomaly labels",
        native_code_url="",
        native_code_license="",
    )
    card.grade()
    return DatasetD0(
        card=card,
        role="NORMAL_ONLY_OPTIONAL — healthy dynamics pretraining only",
        status="AVAILABLE_NORMAL_ONLY",
        canonical_paper="classic inverse-dynamics benchmark distributed with Rasmussen & Williams GPML",
        data_files=[
            {
                "key": "sarcos_inv.mat",
                "size_bytes": 9_964_616,
                "last_modified": "Tue, 01 Jul 2025 12:45:41 GMT",
                "etag": '"6863d875-980c48"',
                "sha256": "b8a249733253ba6097372fedee7696833fcf30de42037d5b4a7227f21a6d1d97",
                "verified_shape": "(44484, 28)",
                "downloaded": True,
            },
            {
                "key": "sarcos_inv_test.mat",
                "size_bytes": 996_776,
                "last_modified": "Tue, 01 Jul 2025 12:45:41 GMT",
                "etag": '"6863d875-f35a8"',
                "sha256": "161a59b5c3b4f4b404584323f181607b2acbe620eb134dc720760dc3f38f5cec",
                "verified_shape": "(4449, 28)",
                "downloaded": True,
            },
        ],
        license_notes="No license statement is published on the distribution page.",
        redistribution_note="Not redistributed.",
        split_definition="official train/test .mat files, row counts verified from the files",
        normalization="none published",
        native_baseline="GP / regression baselines from the GPML literature",
        open_verifications=[
            "No license statement exists; use stays local-analysis only.",
            "SAMPLING RATE IS UNVERIFIED AT SOURCE. The gaussianprocess.org distribution "
            "page states no rate, and the .mat files carry no timestamp column -- 28 "
            "columns are 7 position, 7 velocity, 7 acceleration, 7 torque and nothing "
            "else. A rate from the wider literature is NOT imported here: without it, "
            "any per-second quantity (false alarms/hour, detection delay) is unavailable "
            "for this dataset, which is acceptable because SARCOS is regression-only.",
            "Column ORDER within each block of 7 is assumed from the classic description "
            "and is not verified against a joint naming table; nothing in this round "
            "depends on which joint is which.",
            "SIZE-EVIDENCE TRAP, resolved. gaussianprocess.org (GitHub Pages) gzips these "
            "files on the wire. A request that accepts gzip is answered with "
            "Content-Length 6,206,301 and a WEAK ETag W/\"6863d875-980c48\"; a request "
            "with Accept-Encoding: identity is answered with Content-Length 9,964,616 and "
            "the STRONG ETag \"6863d875-980c48\" -- and 0x980c48 = 9,964,616, so the weak "
            "ETag encoded the true size all along. An earlier probe recorded the "
            "compressed length as the file size, which made every correct download look "
            "truncated. Both the probe and the acquisition path now send "
            "Accept-Encoding: identity and record Content-Encoding, so Content-Length is "
            "always the size of the object being stored.",
        ],
        allowed_claims=["healthy inverse-dynamics representation pretraining"],
        forbidden_claims=[
            "counting SARCOS as fault or anomaly evidence — it contains no anomalies and no anomaly labels",
        ],
        evidence=["sarcos/gpml.txt", "sarcos/train_headers.txt", "sarcos/test_headers.txt"],
    )


LICENSE_COLUMNS = (
    "dataset_id", "license_id", "license_verified", "redistribution_allowed",
    "noncommercial_only", "code_license", "license_notes", "redistribution_note",
)
SCHEMA_COLUMNS = (
    "dataset_id", "channel_count", "sampling_rate_hz", "episode_unit", "signal_group",
    "channels", "group_channel_count",
)
APPLICABILITY_COLUMNS = (
    "dataset_id", "physics_grade", "role", "status", "permitted_adapters",
    "forbidden_adapters", "allowed_claims", "forbidden_claims", "open_verifications",
)
ALL_ADAPTERS = (
    "joint_gru_public", "chain_gnn_public", "geometry_aware_chain_public",
    "frame_aug_chain_public", "rnea_gmo_public", "mobnet_like_public",
)


def write_matrices(records: list[DatasetD0], out_dir: Path, run_id: str, config_sha: str) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    feasibility = out_dir / "dataset_feasibility_matrix.csv"
    with feasibility.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=(*CARD_CSV_COLUMNS, "role", "status", "canonical_citation_year"))
        writer.writeheader()
        for record in records:
            row = record.card.as_csv_row()
            row.update(
                role=record.role,
                status=record.status,
                canonical_citation_year=record.canonical_citation_year,
            )
            writer.writerow(row)
    paths["dataset_feasibility_matrix.csv"] = feasibility

    licenses = out_dir / "dataset_license_matrix.csv"
    with licenses.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LICENSE_COLUMNS)
        writer.writeheader()
        for record in records:
            card = record.card
            writer.writerow(
                {
                    "dataset_id": card.dataset_id,
                    "license_id": card.license_id,
                    "license_verified": str(card.license_verified).lower(),
                    "redistribution_allowed": _tri(card.redistribution_allowed),
                    "noncommercial_only": _tri(card.noncommercial_only),
                    "code_license": card.native_code_license,
                    "license_notes": record.license_notes,
                    "redistribution_note": record.redistribution_note,
                }
            )
    paths["dataset_license_matrix.csv"] = licenses

    schema = out_dir / "dataset_signal_schema_matrix.csv"
    with schema.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SCHEMA_COLUMNS)
        writer.writeheader()
        for record in records:
            card = record.card
            groups = record.signal_groups or [{"group": "UNAUDITED", "channels": "", "count": ""}]
            for group in groups:
                writer.writerow(
                    {
                        "dataset_id": card.dataset_id,
                        "channel_count": "" if card.channel_count is None else card.channel_count,
                        "sampling_rate_hz": "" if card.sampling_rate_hz is None else card.sampling_rate_hz,
                        "episode_unit": card.episode_unit,
                        "signal_group": group["group"],
                        "channels": group["channels"],
                        "group_channel_count": group["count"],
                    }
                )
    paths["dataset_signal_schema_matrix.csv"] = schema

    applicability = out_dir / "dataset_applicability_matrix.csv"
    with applicability.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=APPLICABILITY_COLUMNS)
        writer.writeheader()
        for record in records:
            permitted = set(record.card.permitted_adapters)
            writer.writerow(
                {
                    "dataset_id": record.card.dataset_id,
                    "physics_grade": record.card.physics_grade.value,
                    "role": record.role,
                    "status": record.status,
                    "permitted_adapters": "; ".join(sorted(permitted)),
                    "forbidden_adapters": "; ".join(a for a in ALL_ADAPTERS if a not in permitted),
                    "allowed_claims": " | ".join(record.allowed_claims),
                    "forbidden_claims": " | ".join(record.forbidden_claims),
                    "open_verifications": " | ".join(record.open_verifications),
                }
            )
    paths["dataset_applicability_matrix.csv"] = applicability

    download = out_dir / "dataset_download_manifest.json"
    write_manifest(
        download,
        {
            "schema_version": D0_SCHEMA_VERSION,
            "run_id": run_id,
            "config_sha": config_sha,
            "generated_utc": utc_stamp(),
            "planned_download_bytes": sum(
                f.get("size_bytes", 0)
                for r in records
                for f in r.data_files
                if f.get("planned")
            ),
            "all_listed_bytes": sum(r.total_bytes for r in records),
            "datasets": [
                {
                    "dataset_id": r.card.dataset_id,
                    "status": r.status,
                    "official_url": r.card.official_url,
                    "version": r.card.version,
                    "repo_commit": r.repo_commit,
                    "access_route": r.card.access_route,
                    "files": r.data_files,
                    "evidence": r.evidence,
                }
                for r in records
            ],
        },
    )
    paths["dataset_download_manifest.json"] = download

    issues = out_dir / "dataset_known_issues.md"
    issues.write_text(_render_issues(records), encoding="utf-8")
    paths["dataset_known_issues.md"] = issues
    return paths


def _tri(value: bool | None) -> str:
    return "UNKNOWN" if value is None else str(value).lower()


def _render_issues(records: list[DatasetD0]) -> str:
    lines = [
        "# Dataset known issues — Phase D0",
        "",
        "Each item is an unresolved question or a hazard found while auditing the",
        "official sources. Nothing here is filled in by inference from the robot",
        "model, the paper's prose, or the internal simulator.",
        "",
    ]
    for record in records:
        lines += [f"## {record.card.dataset_id} — {record.status}", ""]
        if record.open_verifications:
            lines += ["**Open verifications**", ""]
            lines += [f"- {item}" for item in record.open_verifications]
            lines.append("")
        if record.leakage_risks:
            lines += ["**Split / leakage**", ""]
            lines += [f"- {item}" for item in record.leakage_risks]
            lines.append("")
        if record.forbidden_claims:
            lines += ["**Forbidden claims**", ""]
            lines += [f"- {item}" for item in record.forbidden_claims]
            lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="certo_fdi_reset.datasets.d0")
    parser.add_argument("--config", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    records = build_cards()
    out_dir = cfg.layout.run_dir(cfg.run_id) / "d0"
    paths = write_matrices(records, out_dir, cfg.run_id, cfg.config_sha)

    for record in records:
        print(
            f"{record.card.dataset_id:16s} {record.card.physics_grade.value:28s} "
            f"{record.status:32s} {record.card.license_id}"
        )
    print()
    for name, path in sorted(paths.items()):
        print(f"  {name:38s} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
