from __future__ import annotations

from dataclasses import replace

import numpy as np

from certo_fdi.operators.linearize import StepLinearization
from certo_fdi.operators.window import assemble_window_operator


def test_window_operator_matches_brute_force_recursion():
    rng = np.random.default_rng(9)
    w, nx, ny, p = 5, 4, 2, 2
    lins = []
    for _ in range(w):
        a = 0.2 * rng.normal(size=(nx, nx))
        e = rng.normal(size=(nx, p))
        c = rng.normal(size=(ny, nx))
        d = rng.normal(size=(ny, p))
        lins.append(StepLinearization(a=a, e=e, c_bar=c, d_bar=d))

    operator = assemble_window_operator(lins, [0, 1])
    u = rng.normal(size=(w, p))
    predicted = operator @ u.reshape(-1)

    x = np.zeros(nx)
    outputs = []
    for k in range(w):
        outputs.append(lins[k].c_bar @ x + lins[k].d_bar @ u[k])
        x = lins[k].a @ x + lins[k].e @ u[k]

    # The generic recursion above emits the direct output before applying E_k,
    # whereas CERTO-FDI defines interval-end output. Shift the brute-force model
    # to the interval-end convention used by the assembled operator.
    x = np.zeros(nx)
    outputs_interval_end = []
    for k in range(w):
        outputs_interval_end.append(lins[k].c_bar @ x + lins[k].d_bar @ u[k])
        x_next = lins[k].a @ x + lins[k].e @ u[k]
        x = x_next

    # Direct construction by superposition under the same convention.
    brute = np.zeros(ny * w)
    for b in range(w):
        x_effect = lins[b].e @ u[b]
        brute[b * ny : (b + 1) * ny] += lins[b].d_bar @ u[b]
        for a in range(b + 1, w):
            brute[a * ny : (a + 1) * ny] += lins[a].c_bar @ x_effect
            x_effect = lins[a].a @ x_effect
    np.testing.assert_allclose(predicted, brute, atol=1e-12, rtol=1e-12)
