# Lattice Condition Generation V2 Axis Spec

Created: 2026-07-08T09:58:26+09:00

## Principle

V2 is failure-map constrained generation, not a larger lattice. The primary lane is min; tick is diagnostic and negative-control only.

## Axes

- lane: min_primary, tick_diagnostic
- time regime: morning composite, midday watch, late risk watch
- coverage: daily floor repair, low-frequency control, holdout control
- risk: MDD fragments with explicit caps
- signal component pool: price position, volume/amount, strength rate, prevday active, seed lineage component
- sell profile: default TP3/SL3/H90 benchmark plus controlled diversity
- lineage: repair composite, Plan D rank lineage, negative lattice control, holdout survivor control

## Rule

No candidate may exist only because a Cartesian axis cell exists. Every candidate must cite a failure-map reason.
