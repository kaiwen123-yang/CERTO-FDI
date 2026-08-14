from __future__ import annotations

import math

import numpy as np


def legacy_covariance_bound(
    covariance_norm: float,
    dimension: int,
    sample_count: int,
    alpha: float = 0.05,
) -> float:
    """Archived heuristic shape, retained only as a falsification target.

    The leading factor three is explicit; the unproved tunable constant in the
    archived claim was set to one. This is deliberately not exposed as a valid
    finite-sample theorem.
    """

    return float(
        3.0
        * covariance_norm
        * (
            math.sqrt(dimension / sample_count)
            + math.sqrt(math.log(1.0 / alpha) / sample_count)
        )
    )


def unit_variance_samples(
    distribution: str,
    rng: np.random.Generator,
    sample_count: int,
    dimension: int,
) -> np.ndarray:
    if distribution == "gaussian":
        return rng.normal(size=(sample_count, dimension))
    if distribution == "t3":
        return rng.standard_t(df=3, size=(sample_count, dimension)) / math.sqrt(3.0)
    if distribution == "lognormal":
        raw = rng.lognormal(mean=0.0, sigma=1.0, size=(sample_count, dimension))
        mean = math.exp(0.5)
        variance = (math.e - 1.0) * math.e
        return (raw - mean) / math.sqrt(variance)
    raise KeyError(distribution)


def covariance_bound_trial(
    distribution: str,
    dimension: int,
    sample_count: int,
    seed: int,
    alpha: float = 0.05,
) -> dict[str, float | int | str | bool]:
    rng = np.random.default_rng(seed)
    samples = unit_variance_samples(distribution, rng, sample_count, dimension)
    sample_covariance = samples.T @ samples / sample_count
    error = float(np.linalg.norm(sample_covariance - np.eye(dimension), ord=2))
    bound = legacy_covariance_bound(1.0, dimension, sample_count, alpha)
    return {
        "distribution": distribution,
        "m": dimension,
        "N": sample_count,
        "seed": seed,
        "observed_operator_error": error,
        "legacy_bound": bound,
        "violation": error > bound,
    }


def figure_eight_response(parameter: np.ndarray) -> np.ndarray:
    parameter = np.asarray(parameter, dtype=float)
    return np.column_stack([np.sin(parameter), np.sin(2.0 * parameter)])


def nearest_centroid_error(
    separation: float,
    noise_scale: float,
    trials: int,
    seed: int,
) -> float:
    """Two equally likely scalar classes with centers separated by ``separation``."""

    rng = np.random.default_rng(seed)
    labels = rng.integers(0, 2, size=trials)
    centers = (labels - 0.5) * separation
    observations = centers + noise_scale * rng.normal(size=trials)
    predictions = (observations >= 0.0).astype(int)
    return float(np.mean(predictions != labels))


def subspace_external_energy(vector: np.ndarray, basis: np.ndarray) -> float:
    vector = np.asarray(vector, dtype=float).reshape(-1)
    basis = np.asarray(basis, dtype=float)
    q, _ = np.linalg.qr(basis)
    residual = vector - q @ (q.T @ vector)
    return float(np.dot(residual, residual) / max(np.dot(vector, vector), 1e-30))
