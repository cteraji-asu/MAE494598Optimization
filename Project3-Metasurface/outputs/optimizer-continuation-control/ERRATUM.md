# Frozen-protocol erratum, 21 October 2026

Original protocol SHA-256: `a8bac535c4c58bdb837dfeda38890ebd86e5413838e895096d136208032a56f9`. The protocol bytes are unchanged. This note corrects inherited descriptive metadata, not samples, seeds, objectives, selections or outcomes.

The top-level `no_test_training` phrase "blocked d excluded from training" is stale. This covered follow-up has 256 training geometries, including **16** inside d=[0.195,0.222]. The exclusion applies to distinct validation/test geometries, not to the entire blocked interval. The actual `designs` array and sampling code are authoritative. Train and held-out d sets have no exact intersection.

For this optimizer comparison, validation really is diagnostic only: both arms use their terminal last-accepted iterate, with no validation checkpoint selection. The nested `optimizer_control` specifies the continuation budget of 1,200 full objective-gradient calls. Other inherited primary-study fields such as `steps` describe the starting study, not extra continuation work. Seeds 1 and 2 were conditional candidates; the failed pilot gate left only seed 0 executed. Equal calls do not mean equal runtime or accepted updates.
