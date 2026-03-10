"""Format clump properties for display."""

from ..data.clumps import ClumpProperties


def format_clump_properties(clump: ClumpProperties) -> dict:
    """Format a single clump's properties for display in the UI."""
    return {
        "Clump ID": clump.clump_id,
        "Component": clump.component.capitalize(),
        "Inside disk": "Yes" if clump.inside else "No",
        "Area (pixels)": clump.area_pix,
        "Area (arcsec\u00b2)": f"{clump.area_arcsec2:.4f}",
        "Area (kpc\u00b2)": f"{clump.area_kpc2:.4f}",
        "R_eff (arcsec)": f"{clump.r_eff_arcsec:.4f}",
        "R_eff (kpc)": f"{clump.r_eff_kpc:.4f}",
        "Centroid x": f"{clump.x0:.1f}",
        "Centroid y": f"{clump.y0:.1f}",
    }
