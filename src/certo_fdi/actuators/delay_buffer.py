from __future__ import annotations

import jax.numpy as jnp


def delayed_command(
    current: jnp.ndarray,
    previous_1: jnp.ndarray,
    previous_2: jnp.ndarray,
    delay_seconds: jnp.ndarray,
    dt: float,
) -> jnp.ndarray:
    """Two-interval explicit history model, piecewise linear in delay.

    The represented physical range is ``0 <= delay <= 2*dt``. Negative values
    are allowed only as a local AD extension at the healthy boundary.
    """

    delay = jnp.asarray(delay_seconds).reshape(())
    first = current + (delay / dt) * (previous_1 - current)
    second = previous_1 + ((delay - dt) / dt) * (previous_2 - previous_1)
    return jnp.where(delay <= dt, first, second)
