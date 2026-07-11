"""TMAC CI layer — orchestration utilities for CI/CD-native scanning.

This package provides:
- git_diff: compute the Changed_File_Set from git refs
- secrets: token reading and secret redaction
- comment: PR/MR comment formatting
- publisher: idempotent GitHub/GitLab comment publishing
- runner: CIRunner orchestrator
"""
