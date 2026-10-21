# Frozen-protocol erratum, 21 October 2026

Original protocol SHA-256: `f72c20160f80341bb93cc8f849450798c49a39b22ff059e224c6aca37320e877`. The protocol bytes are unchanged. This note corrects inherited descriptive metadata, not samples, seeds, objectives, selections or outcomes.

The top-level `no_test_training` phrase "blocked d excluded from training" is stale. This covered follow-up has 256 training geometries, including **16** inside d=[0.195,0.222]. The exclusion applies to distinct validation/test geometries, not to the entire blocked interval. The actual `designs` array and sampling code are authoritative. Train and held-out d sets have no exact intersection.

The inherited `hyperparameter_selection` wording "Validation diagnostic only" is also incomplete. All six fits spend 4,000 gradient calls; validation selects the checkpoint with minimum overall complex port-reflection RMS among fixed steps 0,500,...,4000. It does not select hyperparameters or stop training early. The specific `controls.selection`, selected-step records and pre-final selection seal are authoritative. All six validation gates failed. The final blocked set has no feasible cases, so sensitivity is undefined.
