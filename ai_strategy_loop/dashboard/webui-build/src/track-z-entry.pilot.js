// track-z-entry.pilot.js — Track Z (PR-1) FLAGGED pilot entry module (STOM_BUNDLE=1).
//   Proof-of-concept ESM bundle root. NOT the full app: it imports ONLY the pilot file
//   (phase-detail.jsx, converted to ESM) so esbuild `bundle:true` proves the mechanism
//   on a tiny graph before any fan-out (Story 3 converts the rest).
//
//   Mechanism under test (Driver-2):
//     - phase-detail.jsx's hooks resolve `react` -> webui-build/src/react-shim.js (aliased
//       in build-app.mjs), which re-exports `window.React`. No React copy is bundled.
//     - This entry re-publishes the pilot's cross-consumed shared components on `window`
//       so the FROZEN inline/classic mounts keep seeing them (the IIFE hides bare decls).
//
//   Extended in Story 3 to import + republish the full FROZEN/shared set. For PR-1 the
//   surface is intentionally just the pilot symbols.
import { DemoBadge, LivePending } from "../../frontend/phase-detail.jsx";

Object.assign(window, { DemoBadge, LivePending });
