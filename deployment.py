"""Deployment settings. Database access requires explicit opt-in.

This setting does not verify network exposure or provide authentication.
"""

import os


def is_local_deployment() -> bool:
    """Enable the dataset database only for explicit local mode."""
    return os.environ.get("ITR_DEPLOYMENT", "").strip().lower() == "local"
