// react-dom-shim.js — Track Z (PR-1) Driver-2 alias-to-virtual-shim for react-dom.
//   Re-exports the already-loaded vendored global `window.ReactDOM` (classic script,
//   NOT an npm dep). Aliased from the bare specifier `react-dom` in the esbuild build
//   options so a bundled `import { createRoot } from "react-dom"` resolves to the
//   vendored global with no runtime `require("react-dom")` and no second ReactDOM copy.
const ReactDOM = window.ReactDOM;

export default ReactDOM;

export const {
  createRoot,
  hydrateRoot,
  createPortal,
  flushSync,
  render,
  unmountComponentAtNode,
  findDOMNode,
  version,
} = ReactDOM;
