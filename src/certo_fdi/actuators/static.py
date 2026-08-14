from __future__ import annotations

import jax.numpy as jnp


def apply_efficiency(command: jnp.ndarray, efficiency_loss: jnp.ndarray) -> jnp.ndarray:
    return (1.0 - efficiency_loss) * command
