// react-jsx-runtime-shim.js — maps React 17+ JSX runtime imports to the vendored global React.
// @xyflow/react is bundled into the served app.js, while React itself remains the already-loaded
// classic vendor script. Keep this shim tiny so no second React copy or runtime require is emitted.
const React = window.React;

export const Fragment = React.Fragment;

function withKey(props, key) {
  return key === undefined ? props : { ...props, key };
}

export function jsx(type, props, key) {
  return React.createElement(type, withKey(props, key));
}

export function jsxs(type, props, key) {
  return React.createElement(type, withKey(props, key));
}

export function jsxDEV(type, props, key) {
  return React.createElement(type, withKey(props, key));
}
