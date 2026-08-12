// Re-render a component whenever the shared store emits. Coarse but sufficient:
// the chrome is small and updates are user-driven.
import { useEffect, useReducer } from "preact/hooks";
import { subscribe } from "./state";

export function useStore(): void {
  const [, force] = useReducer((n: number, _action: void) => n + 1, 0);
  useEffect(() => subscribe(() => force()), []);
}
