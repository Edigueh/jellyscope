"""Format clump properties for displaying it with Plotly."""

from jellyscope.data.model.clumps import ClumpProperties
from jellyscope.model.display import ClumpDetailDisplay, DisplayEntry


def format_clump_properties(clump: ClumpProperties) -> ClumpDetailDisplay:
    """Format a single clump's properties as an ordered display table."""
    ra_str = f"{clump.ra_deg:.6f}" if clump.ra_deg is not None else "—"
    dec_str = f"{clump.dec_deg:.6f}" if clump.dec_deg is not None else "—"
    rows: list[tuple[str, str]] = [
        ("Clump ID", str(clump.clump_id)),
        ("Component", clump.component.capitalize()),
        ("Inside disk", "Yes" if clump.inside else "No"),
        ("Area (pixels)", str(clump.area_pix)),
        ("Area (arcsec²)", f"{clump.area_arcsec2:.4f}"),
        ("Area (kpc²)", f"{clump.area_kpc2:.4f}"),
        ("R_eff (arcsec)", f"{clump.r_eff_arcsec:.4f}"),
        ("R_eff (kpc)", f"{clump.r_eff_kpc:.4f}"),
        ("Centroid x", f"{clump.x0:.1f}"),
        ("Centroid y", f"{clump.y0:.1f}"),
        ("RA (deg)", ra_str),
        ("Dec (deg)", dec_str),
    ]
    return ClumpDetailDisplay(
        entries=[DisplayEntry(label=label, value=value) for label, value in rows]
    )
