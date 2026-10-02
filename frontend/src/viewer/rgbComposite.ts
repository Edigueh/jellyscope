export type RGBMethod = "percentile_asinh" | "lupton";

function finiteValues(data: Float64Array): number[] {
  return Array.from(data).filter(Number.isFinite);
}

function percentile(values: number[], percent: number): number {
  if (!values.length) return 0;
  const sorted = values.slice().sort((a, b) => a - b);
  const position = ((sorted.length - 1) * percent) / 100;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

function sigmaClippedStats(data: Float64Array): { median: number; sigma: number } {
  let values = finiteValues(data);
  if (!values.length) return { median: 0, sigma: 1 };

  for (let iteration = 0; iteration < 5; iteration += 1) {
    const median = percentile(values, 50);
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const sigma = Math.sqrt(
      values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length,
    );
    if (!sigma) return { median, sigma: 0 };
    const clipped = values.filter((value) => Math.abs(value - median) <= 3 * sigma);
    if (clipped.length === values.length) return { median, sigma };
    values = clipped;
  }
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return {
    median: percentile(values, 50),
    sigma: Math.sqrt(values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length),
  };
}

function percentileAsinhBand(band: Float64Array): Float64Array {
  const values = finiteValues(band);
  const result = new Float64Array(band.length);
  if (!values.length) return result;

  const background = percentile(values, 50);
  const shifted = values.map((value) => value - background);
  const low = percentile(shifted, 10);
  const high = percentile(shifted, 99.9);
  const denominator = high > low ? high - low : 1;
  const scale = 0.1;

  for (let i = 0; i < band.length; i += 1) {
    if (!Number.isFinite(band[i])) continue;
    let value = (band[i] - background - low) / denominator;
    value = Math.max(0, Math.min(1, value));
    value = Math.asinh(value / scale) / Math.asinh(1 / scale);
    result[i] = value < 0.05 ? 0 : Math.max(0, Math.min(1, value));
  }
  return result;
}

function toByte(value: number): number {
  return Math.max(0, Math.min(255, Math.floor(value * 255)));
}

export function composeRgb(
  rData: Float64Array,
  gData: Float64Array,
  bData: Float64Array,
  method: RGBMethod,
  softening: number,
): Uint8Array {
  const count = rData.length;
  const output = new Uint8Array(count * 3);

  if (method === "percentile_asinh") {
    const r = percentileAsinhBand(rData);
    const g = percentileAsinhBand(gData);
    const b = percentileAsinhBand(bData);
    for (let i = 0; i < count; i += 1) {
      const offset = i * 3;
      output[offset] = toByte(r[i]);
      output[offset + 1] = toByte(g[i] * 1.02);
      output[offset + 2] = toByte(b[i] * 1.02);
    }
    return output;
  }

  const intensity = new Float64Array(count);
  for (let i = 0; i < count; i += 1) intensity[i] = (rData[i] + gData[i] + bData[i]) / 3;
  const { median, sigma } = sigmaClippedStats(intensity);
  const alpha = 0.02 / (sigma + 1e-10);
  const red = new Float64Array(count);
  const green = new Float64Array(count);
  const blue = new Float64Array(count);
  const positive: number[] = [];

  for (let i = 0; i < count; i += 1) {
    const shifted = intensity[i] - median;
    const factor = shifted > 0 ? Math.asinh(alpha * softening * shifted) / softening / shifted : 0;
    red[i] = Math.max(rData[i] - median, 0) * factor;
    green[i] = Math.max(gData[i] - median, 0) * factor;
    blue[i] = Math.max(bData[i] - median, 0) * factor;
    const maxRgb = Math.max(red[i], green[i], blue[i]);
    if (maxRgb > 1) {
      red[i] /= maxRgb;
      green[i] /= maxRgb;
      blue[i] /= maxRgb;
    }
    if (Number.isFinite(rData[i]) && Number.isFinite(gData[i]) && Number.isFinite(bData[i])) {
      if (red[i] > 0) positive.push(red[i]);
      if (green[i] > 0) positive.push(green[i]);
      if (blue[i] > 0) positive.push(blue[i]);
    } else {
      red[i] = 0;
      green[i] = 0;
      blue[i] = 0;
    }
  }

  const vmax = positive.length ? percentile(positive, 99.5) : 1;
  for (let i = 0; i < count; i += 1) {
    const offset = i * 3;
    output[offset] = toByte(vmax > 0 ? red[i] / vmax : red[i]);
    output[offset + 1] = toByte(vmax > 0 ? green[i] / vmax : green[i]);
    output[offset + 2] = toByte(vmax > 0 ? blue[i] / vmax : blue[i]);
  }
  return output;
}

export function rgbToPngDataUrl(rgb: Uint8Array, width: number, height: number): string {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas 2D context is unavailable");

  const image = context.createImageData(width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const source = (y * width + x) * 3;
      const target = ((height - 1 - y) * width + x) * 4;
      image.data[target] = rgb[source];
      image.data[target + 1] = rgb[source + 1];
      image.data[target + 2] = rgb[source + 2];
      image.data[target + 3] = 255;
    }
  }
  context.putImageData(image, 0, 0);
  return canvas.toDataURL("image/png");
}
