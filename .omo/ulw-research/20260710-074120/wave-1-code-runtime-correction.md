# Wave 1 correction — context-pack reachability

- Earlier preliminary note suggesting context-pack/candidate-pack had no production caller anywhere is withdrawn.
- `brain/context_pack_builder.py` and `brain/pack_producer.py` are called by the separate `cli/research_loop.py` discovery pipeline.
- They remain outside autonomous `controller/loop.py`, default-OFF, and apparently are not exposed by the ordinary `stom_backtest.py discovery research` CLI parser.
- Therefore the narrower architectural-separation/default-reachability concern remains open and is being independently verified.

