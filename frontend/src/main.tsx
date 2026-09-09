import { render } from "preact";
import "./styles.css";
import { App } from "./components/App";
import { initState } from "./state";

async function boot(): Promise<void> {
  await initState();
  const root = document.getElementById("app");
  if (root) render(<App />, root);
}

void boot();
