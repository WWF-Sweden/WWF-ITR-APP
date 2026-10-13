"""CTA selection, validation, and persistent storage shared by the app."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time

import pandas as pd
from ITR.configs import PortfolioCoverageTVPConfig
from ITR.data.sbti import SBTi

CTA_PATH = Path(os.environ.get("ITR_CTA_PATH", "data/cta/current-Companies-Taking-Action.xlsx")).resolve()
_CTA_LOCK = threading.RLock()


class CTAError(RuntimeError):
    """CTA data cannot be used safely."""


def validate_cta(path):
    try:
        frame = pd.read_excel(path)
        required = [PortfolioCoverageTVPConfig.COL_COMPANY_NAME,
                    PortfolioCoverageTVPConfig.COL_COMPANY_ISIN,
                    PortfolioCoverageTVPConfig.COL_COMPANY_LEI,
                    PortfolioCoverageTVPConfig.COL_TARGET]
        missing = set(required) - set(frame.columns)
        if missing or frame.empty:
            raise ValueError("missing columns: " + ", ".join(sorted(missing)) if missing else "file is empty")
    except Exception as exc:
        raise CTAError(f"CTA file is missing or invalid ({path}): {exc}") from exc
    return str(Path(path).resolve())


def cta_fingerprint(path):
    """Include contents so replacing a file at the same path invalidates results."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_cta_config(path):
    class LocalCTAConfig(PortfolioCoverageTVPConfig):
        FILE_TARGETS = str(path)
        FILE_TARGETS_CUSTOM_PATH = str(path)
        USE_LOCAL_CTA = True
        OFFLINE = True
    return LocalCTAConfig


@contextmanager
def temperature_cta_context(path):
    # TemperatureScore's SBTi enrichment uses the package's default config and
    # mutates it. Serialize access and restore it to prevent cross-session leaks.
    with _CTA_LOCK:
        names = ("FILE_TARGETS", "FILE_TARGETS_CUSTOM_PATH", "USE_LOCAL_CTA", "OFFLINE")
        previous = {name: (name in vars(PortfolioCoverageTVPConfig), getattr(PortfolioCoverageTVPConfig, name, None)) for name in names}
        try:
            if path:
                config = local_cta_config(path)
                for name in names:
                    setattr(PortfolioCoverageTVPConfig, name, getattr(config, name))
            yield
        finally:
            for name, (owned, value) in previous.items():
                if owned:
                    setattr(PortfolioCoverageTVPConfig, name, value)
                elif name in vars(PortfolioCoverageTVPConfig):
                    delattr(PortfolioCoverageTVPConfig, name)


def refresh_cta():
    """Use the package downloader; replace the persistent file only after validation."""
    with _CTA_LOCK:
        CTA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=CTA_PATH.parent) as directory:
            candidate = Path(directory) / CTA_PATH.name
            downloader = SBTi.__new__(SBTi)
            downloader.c = local_cta_config(candidate)
            try:
                downloader._fetch_and_save_cta_file()
                validate_cta(candidate)
                os.replace(candidate, CTA_PATH)
            except Exception as exc:
                raise CTAError(f"Could not update CTA from SBTi: {exc}") from exc
        return str(CTA_PATH)


def resolve_cta(custom_path=None, offline=False):
    """Return the actual file and any fallback warning. Uploads never download."""
    if custom_path:
        return validate_cta(custom_path), None
    offline = offline or os.environ.get("ITR_OFFLINE", "").lower() in ("1", "true", "yes")
    warning = None
    with _CTA_LOCK:
        if not offline and (not CTA_PATH.exists() or time.time() - CTA_PATH.stat().st_mtime > 7 * 86400):
            try:
                refresh_cta()
            except CTAError as exc:
                warning = str(exc)
        if not CTA_PATH.exists():
            import ITR.data.sbti as sbti_module
            bundled = Path(sbti_module.__file__).resolve().parent.parent / "inputs" / "current-Companies-Taking-Action.xlsx"
            validate_cta(bundled)
            CTA_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, CTA_PATH)
            warning = (warning + " " if warning else "") + "Using bundled CTA data; it may be outdated."
        return validate_cta(CTA_PATH), warning


def store_cta_upload(state, upload):
    """Reuse an unchanged upload and remove the previous session temporary file."""
    content = upload.getvalue() if upload is not None else None
    digest = hashlib.sha256(content).hexdigest() if content is not None else None
    previous = state.get("_cta_upload_path")
    if digest == state.get("_cta_upload_digest") and previous and Path(previous).exists():
        return previous
    replacement = None
    if content is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(upload.name).suffix) as handle:
            handle.write(content)
            replacement = handle.name
    if previous:
        Path(previous).unlink(missing_ok=True)
    state["_cta_upload_path"] = replacement
    state["_cta_upload_digest"] = digest
    return replacement
