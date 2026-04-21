"""Device reference resolution for LabSmith UI flow steps.

This module is deliberately UI-neutral and hardware-neutral: it consumes the
plain dictionaries returned by ``LabsmithBoard.connected_devices()`` and does
not import Qt or uProcess.
"""
import re
from typing import Any, Dict, List, Optional


LEGACY_SYRINGE_RE = re.compile(r"^SPS01_(\d+)$")
LEGACY_MANIFOLD_RE = re.compile(r"^C4VM_(\d+)$")


def _copy_match(device: Dict[str, Any], matched_via: str) -> Dict[str, Any]:
    out = dict(device)
    out["matched_via"] = matched_via
    return out


def resolve_device_ref(
    kind: str,
    ref: str,
    devices: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Resolve a user/JSON device reference to a connected device dictionary.

    Resolution order:
      1. Exact current hardware name match.
      2. Exact stringified address match.
      3. Legacy index fallback:
         ``SPS01_<N>`` maps to syringe index ``N - 1``.
         ``C4VM_<N>`` maps to the first connected manifold.
      4. ``None`` when unresolved.
    """
    device_kind = str(kind or "").strip().lower()
    text = str(ref or "").strip()
    if device_kind not in ("syringe", "manifold") or not text:
        return None

    candidates = [
        d for d in devices
        if str(d.get("type", "")).strip().lower() == device_kind
    ]
    for device in candidates:
        if str(device.get("name", "")).strip() == text:
            return _copy_match(device, "exact")

    for device in candidates:
        addr = device.get("addr")
        if addr is not None and str(addr).strip() == text:
            return _copy_match(device, "addr")

    if device_kind == "syringe":
        m = LEGACY_SYRINGE_RE.match(text)
        if m:
            legacy_index = int(m.group(1)) - 1
            for device in candidates:
                if device.get("index") == legacy_index:
                    return _copy_match(device, "legacy_index")
    elif device_kind == "manifold":
        if LEGACY_MANIFOLD_RE.match(text) and candidates:
            return _copy_match(candidates[0], "legacy_index")

    return None
