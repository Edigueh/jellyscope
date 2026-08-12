# Product

## Register

product

## Platform

web

## Users

Astrophysical scientists studying JWST NIRCam observations of jellyfish
galaxies — cluster galaxies whose gas is being stripped into tails of
star-forming clumps by ram pressure. They arrive with a specific galaxy in
mind, fluent in FITS, WCS, NIRCam filters, and flux stretches, and want to
interrogate a datacube and its clump catalog directly: compare morphology
across wavelength bands, inspect individual clumps' physical properties, and
measure their positions and separations on the sky. Context is a research
workstation on a large display, often alongside other analysis tools.

## Product Purpose

Jellyscope is an interactive explorer for JWST NIRCam jellyfish-galaxy
datacubes (FITS) and their clump catalogs (CSV). It renders single-band
heatmaps and multi-band RGB composites with scientifically faithful stretches,
overlays detected clump boundaries and centroids, and exposes each clump's
measured properties (area, effective radius, sky position) and pairwise angular
separations. Success is a scientist trusting the tool enough to reach for it
when reasoning about a galaxy — the interface disappears into the data.

## Positioning

A focused, canvas-first viewer that puts JWST jellyfish datacubes and their
clump catalogs in one place, where the image is the interface and every
measurement is one click away.

## Brand Personality

Precise, quiet, instrument-like. The chrome recedes so the data leads; numbers
are exact and monospaced; color belongs to the science (the colormaps, the RGB
composite), not the furniture. It should feel like a professional observatory
instrument — Aladin Lite, DS9 — not a consumer dashboard.

## Anti-references

The prior iteration: a purple-navy palette with a neon-cyan accent, a heavy
title header, one crammed control bar, uniform tiny type, boxed panels. More
broadly: SaaS-dashboard aesthetics, decorative gradients, glassmorphism for
flavor, any chrome hue that competes with the scientific colormaps.

## Design Principles

- **The data leads.** The datacube fills the viewport; chrome floats over it
  and gets out of the way. Every pixel spent on furniture is a pixel not spent
  on the image.
- **Measurements are exact.** All numerics — RA/Dec, wavelengths, areas, radii,
  IDs — are monospaced and tabular so columns of figures scan cleanly.
- **Colour belongs to the science.** The palette is a neutral near-black slate
  with one restrained accent; the only saturated colour on screen is the
  scientific colormap and the RGB composite.
- **Earned familiarity over novelty.** Standard affordances (segmented toggles,
  a docked inspector, keyboard shortcuts) behave the way a fluent user expects.
- **Nothing hidden that's already built.** Surface every real capability the
  backend supports rather than leaving it unreachable.

## Accessibility & Inclusion

Keyboard shortcuts for every primary action; visible focus rings throughout
(never removed without replacement); `prefers-reduced-motion` honored (all
transitions collapse to instant). Body and label text verified ≥4.5:1 against
its surface. Colormap choice is user-selectable (Viridis default is
colorblind-friendly).
