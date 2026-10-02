"""Format clump properties for displaying it with Plotly."""

import math

from jellyscope.data.model.clumps import ClumpProperties
from jellyscope.model.display import ClumpDetailDisplay, DisplayEntry


def _fmt_opt(value: float | None, spec: str = ".4f") -> str:
    return "—" if value is None else format(value, spec)


def _fmt_opt_bool(value: bool | None) -> str:
    if value is None:
        return "—"
    return "Yes" if value else "No"


def format_clump_properties(clump: ClumpProperties) -> ClumpDetailDisplay:
    """Format a single clump's properties as an ordered display table."""
    ra_str = f"{clump.ra_deg:.6f}" if clump.ra_deg is not None else "—"
    dec_str = f"{clump.dec_deg:.6f}" if clump.dec_deg is not None else "—"
    rows: list[tuple[str, str]] = [
        ("Clump ID", str(clump.clump_id)),
        ("Component", clump.component.capitalize()),
        ("Inside disk", _fmt_opt_bool(clump.inside)),
        ("Area (pixels)", str(clump.area_pix)),
        ("Area (arcsec²)", f"{clump.area_arcsec2:.4f}"),
        ("Area (kpc²)", f"{clump.area_kpc2:.4f}"),
        ("R_eff (arcsec)", _fmt_opt(clump.r_eff_arcsec)),
        ("R_eff (kpc)", _fmt_opt(clump.r_eff_kpc)),
        ("Centroid x", f"{clump.x0:.1f}"),
        ("Centroid y", f"{clump.y0:.1f}"),
        ("RA (deg)", ra_str),
        ("Dec (deg)", dec_str),
    ]

    if clump.mass is not None and clump.mass > 0:
        rows.append(("log M★ (M☉)", f"{math.log10(clump.mass):.3f}"))

    sed_rows: list[tuple[str, str, str]] = [
        ("SFR (M☉/yr)", "sfr_avg", ".4f"),
        ("sSFR (yr⁻¹)", "ssfr_avg", ".3e"),
        ("log Z/Z☉", "logzsol", ".3f"),
        ("Dust τ₂", "dust2", ".3f"),
        ("Age (Gyr)", "tage", ".3f"),
        ("log U (gas)", "gas_logu", ".2f"),
    ]
    for label, attr, spec in sed_rows:
        val = getattr(clump, attr)
        if val is not None:
            rows.append((label, format(val, spec)))

    return ClumpDetailDisplay(
        entries=[DisplayEntry(label=label, value=value) for label, value in rows]
    )
