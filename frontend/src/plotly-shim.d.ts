// plotly.js-dist-min ships no type declarations. We use Plotly loosely in the
// science core (untyped graph div), so a minimal ambient declaration is enough.
// Full dist is required: the app uses heatmap + image traces, which the basic
// dist does not bundle.
declare module "plotly.js-dist-min" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Plotly: any;
  export default Plotly;
}
