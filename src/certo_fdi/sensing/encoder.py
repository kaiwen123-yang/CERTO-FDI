from __future__ import annotations

import jax.numpy as jnp


def measured_state(
    q: jnp.ndarray,
    velocity: jnp.ndarray,
    encoder_bias: jnp.ndarray,
) -> tuple[jnp.ndarray, jnp.ndarray]:
    return q + encoder_bias, velocity
