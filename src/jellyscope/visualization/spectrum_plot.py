"""Plotly figure builders for spectral energy distribution (SED) plots."""


def create_sed_figure(spectrum: dict, title: str = "Spectral Energy Distribution") -> dict:
    """Create a Plotly scatter plot of flux vs wavelength.

    Args:
        spectrum: Dict with 'wavelengths', 'mean_flux' (or 'fluxes'), and optionally 'std_flux'.
        title: Plot title.
    """
    wavelengths = spectrum["wavelengths"]
    fluxes = spectrum.get("mean_flux") or spectrum.get("fluxes", [])
    filter_names = spectrum.get("filter_names", [])

    traces = [
        {
            "type": "scatter",
            "x": wavelengths,
            "y": fluxes,
            "mode": "lines+markers",
            "marker": {"size": 7, "color": "#00ccff"},
            "line": {"color": "#00ccff", "width": 2},
            "text": filter_names,
            "hovertemplate": (
                "%{text}<br>\u03bb: %{x:.3f} \u00b5m<br>Flux: %{y:.4e}<extra></extra>"
            ),
            "name": "SED",
        }
    ]

    if "std_flux" in spectrum:
        std = spectrum["std_flux"]
        upper = [
            (f + s) if f is not None and s is not None else None
            for f, s in zip(fluxes, std, strict=True)
        ]
        lower = [
            (f - s) if f is not None and s is not None else None
            for f, s in zip(fluxes, std, strict=True)
        ]
        traces.append(
            {
                "type": "scatter",
                "x": wavelengths + wavelengths[::-1],
                "y": upper + lower[::-1],
                "fill": "toself",
                "fillcolor": "rgba(0, 204, 255, 0.15)",
                "line": {"color": "rgba(0,0,0,0)"},
                "hoverinfo": "skip",
                "showlegend": False,
                "name": "\u00b11\u03c3",
            }
        )

    layout = {
        "title": {"text": title, "font": {"color": "#cccccc"}},
        "xaxis": {
            "title": "Wavelength (\u00b5m)",
            "gridcolor": "#333",
            "color": "#999",
        },
        "yaxis": {
            "title": "Flux",
            "gridcolor": "#333",
            "color": "#999",
        },
        "plot_bgcolor": "#1a1a2e",
        "paper_bgcolor": "#16213e",
        "font": {"color": "#cccccc"},
        "margin": {"l": 60, "r": 20, "t": 40, "b": 50},
        "showlegend": False,
    }

    return {"data": traces, "layout": layout}


def create_multi_sed_figure(spectra: list[dict], labels: list[str]) -> dict:
    """Overlay multiple SEDs for comparison."""
    colors = [
        "#00ccff",
        "#ff4444",
        "#44ff44",
        "#ffaa00",
        "#ff44ff",
        "#44ffff",
        "#ffff44",
        "#aa44ff",
    ]
    traces = []
    for i, (spec, label) in enumerate(zip(spectra, labels, strict=True)):
        color = colors[i % len(colors)]
        fluxes = spec.get("mean_flux") or spec.get("fluxes", [])
        traces.append(
            {
                "type": "scatter",
                "x": spec["wavelengths"],
                "y": fluxes,
                "mode": "lines+markers",
                "marker": {"size": 6, "color": color},
                "line": {"color": color, "width": 2},
                "name": label,
                "text": spec.get("filter_names", []),
                "hovertemplate": (
                    f"{label}<br>%{{text}}<br>"
                    "\u03bb: %{x:.3f} \u00b5m<br>Flux: %{y:.4e}<extra></extra>"
                ),
            }
        )

    layout = {
        "title": {"text": "SED Comparison", "font": {"color": "#cccccc"}},
        "xaxis": {
            "title": "Wavelength (\u00b5m)",
            "gridcolor": "#333",
            "color": "#999",
        },
        "yaxis": {
            "title": "Flux",
            "gridcolor": "#333",
            "color": "#999",
        },
        "plot_bgcolor": "#1a1a2e",
        "paper_bgcolor": "#16213e",
        "font": {"color": "#cccccc"},
        "margin": {"l": 60, "r": 20, "t": 40, "b": 50},
        "legend": {"font": {"color": "#cccccc"}},
    }

    return {"data": traces, "layout": layout}
