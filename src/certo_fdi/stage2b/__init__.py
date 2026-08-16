"""Stage 2B: contact load-path localization and context-calibrated sequential monitoring.

The frozen ``chain_gnn_aug`` healthy-residual encoder from Stage 1R-B/2A is reused unchanged --
no new neural encoder is built here. What is new is everything *after* the residual:

``loadpath_controls``      the five source-of-gain controls (support / random / fixed-J /
                           shuffled-time / time-aligned), rank and support matched
``rank_aware_scores``      five pre-registered per-link localization scores
``contact_calibration``    the separate F4_CAL partition used to pick one score and the reject rule
``selective_localization`` accept/defer with episode-level risk-coverage
``context_calibration``    healthy-only global / Mondrian / quantile-regression / conformal thresholds
``sequential_monitor``     persistence, hysteresis and one-sided CUSUM wrappers
``event_accounting``       the frozen alarm-event, refractory and delay definitions
``healthy_expansion``      the nested H40/H80/H160 healthy datasets
``metrics_stage2b``        episode-cluster bootstrap and the Stage 2B metric tables
``decision_stage2b``       the pre-registered decision rules (committed before any result)
"""
