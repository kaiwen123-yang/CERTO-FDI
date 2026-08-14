import numpy as np

from certo_fdi.certificates.noise_radius import gaussian_oracle_radius, whiten


def test_general_spd_whitening_matches_mahalanobis_norm():
    covariance = np.array([[2.0, 0.4], [0.4, 1.0]])
    values = np.array([[1.2, -0.7], [-0.3, 0.8]])
    whitened = whiten(values, covariance)
    inverse = np.linalg.inv(covariance)
    expected = np.einsum("ni,ij,nj->n", values, inverse, values)
    np.testing.assert_allclose(np.sum(whitened**2, axis=1), expected, rtol=1e-12, atol=1e-12)


def test_gaussian_oracle_radius_has_requested_marginal_coverage():
    rng = np.random.default_rng(260809)
    dimension = 8
    sigma = 0.2
    radius = gaussian_oracle_radius(dimension, sigma, 0.05)
    samples = sigma * rng.normal(size=(80_000, dimension))
    coverage = np.mean(np.linalg.norm(samples, axis=1) <= radius)
    assert abs(coverage - 0.95) < 0.005
