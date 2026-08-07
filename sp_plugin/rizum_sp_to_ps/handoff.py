"""Clipboard handoff contract from Painter to the Photoshop UXP plugin."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

HANDOFF_PREFIX = "RIZUM_PT_TO_PS_HANDOFF_V1\n"


def export_list_handoff(export_list_path):
    """Return a single-use Photoshop build instruction for the clipboard."""
    path = Path(export_list_path)
    payload = {
        "protocol": "rizum-pt-to-ps",
        "version": 1,
        "id": uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "action": "build_export_list",
        "path": str(path),
    }
    return HANDOFF_PREFIX + json.dumps(payload, separators=(",", ":"))
