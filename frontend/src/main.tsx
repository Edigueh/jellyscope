import { render } from "preact";
import "./styles.css";
import { App } from "./components/App";

const root = document.getElementById("app");
if (root) render(<App />, root);
