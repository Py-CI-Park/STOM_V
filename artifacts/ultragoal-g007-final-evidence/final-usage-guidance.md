# STOM Dashboard V3 final usage guidance

- V2/default routes remain the baseline: `/ui/evolution`, `/ui/backtest`, and `/ui/chart-replay`.
- V3 remains explicit/selectable only: use `/ui/remodel/<page>` or `dashboard_version=v3` entry points.
- Reference/demo mode is labeled and inert: use `?demo=reference` for review fixtures.
- Live mode is read-only on page load: use `?backend=http://127.0.0.1:<port>` for local loopback-only safe probes.
- Manual controls are human-gated; reference/demo manual controls are disabled and live manual controls are not invoked on page load.
- Safety labels must remain visible: No Live Order, No Broker Login, No Account Trading, Research Only, Human Approval Gate, Append-Only Audit.
