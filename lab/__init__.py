"""The `lab` package — Purple Range's validation CLI + event ledger (T-004).

This package is intentionally thin at this stage: it provides the locked CLI
dispatch table (`lab.cli`) and the versioned ValidationEvent ledger skeleton
(`lab.ledger`). Stream work (S1/S2/S3) fills in command bodies behind the
already-registered dispatch entries; it does not edit the wiring.
"""
