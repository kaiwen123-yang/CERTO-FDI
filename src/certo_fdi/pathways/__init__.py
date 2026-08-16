"""Joint-Cartesian fault-pathway geometry (Stage 2A).

The modules here turn the chain-corrected joint residual ``e_tau`` into *explicit, physical*
fault-pathway dictionaries and the geometric statistics computed from them:

``jacobians``    per-link / per-point Jacobians of the frozen 7-DoF chain (world frame)
``dictionaries`` F1-F6 window dictionaries in the residual coordinates
``whitening``    context-conditional healthy whitening of the window residual
``geometry``     ridge projections, principal angles, Fisher information, ee/null split
``localization`` zero-shot per-link contact localization with rejection
``fusion``       the small auditable fusers used by the ablations

Nothing in this package trains on fault labels; the deployed dictionaries are functions of
measured signals and the nominal model only.
"""
