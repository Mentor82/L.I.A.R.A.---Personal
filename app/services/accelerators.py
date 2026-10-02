"""
Feature flags for the retired direct accelerator hosts (Personal#29 B6-B8).

Hailo-8L (RPi5 192.168.178.15:5000) and the Edge TPU (192.168.178.40/.155:5001)
no longer exist as services: every attempt ran into a connect timeout. Both are
off by default; flip HAILO_ENABLED / EDGETPU_ENABLED in the .env only if a host
comes back. Hailo's real successor is a LiNeP runtime on the RPi5 (vision
profile, Mentor82/LiNeP#32), not these direct REST clients.
"""
from core.config import settings


class AcceleratorDisabledError(RuntimeError):
    """The requested accelerator backend is switched off (no host)."""


def hailo_enabled() -> bool:
    return bool(settings.hailo_enabled)


def edgetpu_enabled() -> bool:
    return bool(settings.edgetpu_enabled)


def require_hailo() -> None:
    if not hailo_enabled():
        raise AcceleratorDisabledError(
            "Hailo ist deaktiviert: der RPi5-Host existiert nicht mehr (HAILO_ENABLED=false). "
            "Vision laeuft kuenftig ueber das LiNeP-Vision-Profil."
        )


def require_edgetpu() -> None:
    if not edgetpu_enabled():
        raise AcceleratorDisabledError(
            "Edge TPU ist deaktiviert: kein Host mehr vorhanden (EDGETPU_ENABLED=false)."
        )
