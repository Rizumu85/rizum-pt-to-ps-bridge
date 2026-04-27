"""UDIM and UV tile helpers."""


def uv_to_udim(u_coord, v_coord):
    """Convert Painter UV tile coordinates to a UDIM number."""
    return 1001 + int(u_coord) + (10 * int(v_coord))
