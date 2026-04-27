"""Blend-mode mapping between Substance Painter and Photoshop."""

from __future__ import annotations

from dataclasses import asdict, dataclass

KEEP_EDITABLE = "keep_editable"
BAKE = "bake"
HIDDEN = "hidden"
NO_BLENDING = "no_blending"

SYNC_BOTH = "both"
SYNC_SP_TO_PS_ONLY = "sp_to_ps_only"
SYNC_NONE = "none"

DIRECT_BLEND_MODES = {
    "Normal": "NORMAL",
    "PassThrough": "PASSTHROUGH",
    "Multiply": "MULTIPLY",
    "Screen": "SCREEN",
    "Overlay": "OVERLAY",
    "Darken": "DARKEN",
    "Lighten": "LIGHTEN",
    "LinearDodge": "LINEARDODGE",
    "LinearBurn": "LINEARBURN",
    "ColorBurn": "COLORBURN",
    "ColorDodge": "COLORDODGE",
    "SoftLight": "SOFTLIGHT",
    "HardLight": "HARDLIGHT",
    "VividLight": "VIVIDLIGHT",
    "LinearLight": "LINEARLIGHT",
    "PinLight": "PINLIGHT",
    "Difference": "DIFFERENCE",
    "Exclusion": "EXCLUSION",
    "Subtract": "SUBTRACT",
    "Divide": "DIVIDE",
    "Saturation": "SATURATION",
    "Color": "COLOR",
}

APPROXIMATE_BLEND_MODES = {
    "Tint": "HUE",
    "Value": "LUMINOSITY",
    "SignedAddition": "LINEARDODGE",
    "InverseDivide": "DIVIDE",
    "InverseSubtract": "SUBTRACT",
    "Replace": "NORMAL",
}

ALWAYS_BAKE_MODES = {
    "NormalMapCombine",
    "NormalMapDetail",
    "NormalMapInverseDetail",
}

DEFAULT_BAKE_MODES = set(APPROXIMATE_BLEND_MODES) | ALWAYS_BAKE_MODES


@dataclass(frozen=True)
class BlendDecision:
    """Photoshop representation decision for one Painter blend mode."""

    painter_mode: str | None
    ps_blend_mode: str | None
    bake_policy: str
    sync_direction: str
    warnings: tuple[str, ...] = ()

    def to_dict(self):
        """Return a JSON-friendly decision object."""
        data = asdict(self)
        data["warnings"] = list(self.warnings)
        return data


def map_blend_mode(painter_mode, preserve_all_layers=False):
    """Return the Photoshop blend mode and bake policy for a Painter mode."""
    mode = _mode_name(painter_mode)

    if mode is None:
        return BlendDecision(None, None, NO_BLENDING, SYNC_NONE).to_dict()

    if mode == "Disable":
        return BlendDecision(
            mode,
            None,
            HIDDEN,
            SYNC_NONE,
            ("Painter Disable mode hides this contribution.",),
        ).to_dict()

    if mode in DIRECT_BLEND_MODES:
        return BlendDecision(
            mode,
            DIRECT_BLEND_MODES[mode],
            KEEP_EDITABLE,
            SYNC_BOTH,
        ).to_dict()

    if mode in ALWAYS_BAKE_MODES:
        return BlendDecision(
            mode,
            None,
            BAKE,
            SYNC_SP_TO_PS_ONLY,
            (f"{mode} has no Photoshop blend-mode equivalent.",),
        ).to_dict()

    if mode in APPROXIMATE_BLEND_MODES:
        ps_mode = APPROXIMATE_BLEND_MODES[mode]
        if preserve_all_layers:
            return BlendDecision(
                mode,
                ps_mode,
                KEEP_EDITABLE,
                SYNC_BOTH,
                (f"{mode} is approximated with Photoshop {ps_mode}.",),
            ).to_dict()

        return BlendDecision(
            mode,
            ps_mode,
            BAKE,
            SYNC_SP_TO_PS_ONLY,
            (f"{mode} is baked in default mode to avoid color drift.",),
        ).to_dict()

    return BlendDecision(
        mode,
        None,
        BAKE,
        SYNC_SP_TO_PS_ONLY,
        (f"Unmapped Painter blend mode {mode}; baking conservatively.",),
    ).to_dict()


def decide_node_blending(blend_modes, preserve_all_layers=False):
    """Collapse per-channel Painter blend modes into node-level decisions."""
    if not blend_modes:
        return {
            "bake_policy": NO_BLENDING,
            "sync_direction": SYNC_NONE,
            "ps_blend_mode": None,
            "blend_decisions": {},
            "warnings": [],
        }

    decisions = {
        channel: map_blend_mode(mode, preserve_all_layers)
        for channel, mode in blend_modes.items()
    }
    policies = {decision["bake_policy"] for decision in decisions.values()}
    sync_directions = {decision["sync_direction"] for decision in decisions.values()}
    ps_modes = {
        decision["ps_blend_mode"]
        for decision in decisions.values()
        if decision["ps_blend_mode"] is not None
    }
    warnings = [
        warning
        for decision in decisions.values()
        for warning in decision["warnings"]
    ]

    return {
        "bake_policy": _collapse_policy(policies),
        "sync_direction": _collapse_sync(sync_directions),
        "ps_blend_mode": ps_modes.pop() if len(ps_modes) == 1 else None,
        "blend_decisions": decisions,
        "warnings": warnings,
    }


def _collapse_policy(policies):
    if BAKE in policies:
        return BAKE
    if HIDDEN in policies:
        return HIDDEN
    if KEEP_EDITABLE in policies:
        return KEEP_EDITABLE
    return NO_BLENDING


def _collapse_sync(sync_directions):
    if SYNC_SP_TO_PS_ONLY in sync_directions:
        return SYNC_SP_TO_PS_ONLY
    if SYNC_BOTH in sync_directions:
        return SYNC_BOTH
    return SYNC_NONE


def _mode_name(value):
    if value is None:
        return None
    return getattr(value, "name", str(value))
