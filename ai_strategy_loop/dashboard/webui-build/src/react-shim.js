// react-shim.js — Track Z (PR-1) Driver-2 alias-to-virtual-shim.
//   esbuild has NO rollup-style `output.globals`, so `external:['react']` + format:iife
//   emits a runtime `require("react")` ("Dynamic require of react is not supported").
//   Instead we ALIAS the bare specifier `react` to this module, which re-exports the
//   ALREADY-LOADED vendored global `window.React` (a classic script, NOT an npm dep).
//   No React source is bundled → single React identity, zero `require("react")`,
//   zero second-React sentinel (`react.development`/`__SECRET_INTERNALS`) in the output.
//
//   The bundled hooks call these named exports; because they are the same object members
//   off `window.React`, `window.React === <the React the bundle's hooks call>` holds.
const React = window.React;

export default React;

export const {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
  useContext,
  useReducer,
  useLayoutEffect,
  useImperativeHandle,
  useDeferredValue,
  useTransition,
  useId,
  useSyncExternalStore,
  useInsertionEffect,
  useDebugValue,
  Fragment,
  createElement,
  cloneElement,
  createContext,
  createRef,
  forwardRef,
  isValidElement,
  memo,
  lazy,
  startTransition,
  Children,
  Component,
  PureComponent,
  StrictMode,
  Suspense,
  Profiler,
  version,
} = React;
