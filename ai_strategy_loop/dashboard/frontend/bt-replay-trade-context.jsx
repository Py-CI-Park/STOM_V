/* Read-only handoff context from QSP7 trade-path analysis into Replay. */
import { _tpTime } from "./bt-trade-path-chart.jsx";
const { useState: useState_tprc, useEffect: useEffect_tprc } = React;

function BtReplayTradeContext() {
  const [context, setContext] = useState_tprc(null);
  useEffect_tprc(() => {
    try { setContext(JSON.parse(localStorage.getItem("stom_trade_path_context") || "null")); } catch (error) { setContext(null); }
  }, []);
  if (!context) return null;
  return <section className="panel tp-replay-context" aria-labelledby="tp-replay-context-title"><header className="panel-hd"><div><div className="stom-section-label" id="tp-replay-context-title">거래 경로 분석에서 전달됨</div><div className="mono">{context.name} · {context.code} · {context.trade_key}</div></div><span className="tp-authority diagnostic">진단</span></header><div className="panel-bd"><div className="tp-marker-row"><span>매수 <b>{_tpTime(context.buy_time)}</b></span><span>실제 매도 <b>{_tpTime(context.sell_time)}</b></span><span>전체청산 <b>{_tpTime(context.boundary)}</b></span></div><p className="mono">Replay는 원시 시계열을 다시 읽습니다. 이 표시는 분석 결과를 매매 신호로 승격하지 않습니다.</p></div></section>;
}

Object.assign(window, { BtReplayTradeContext });
export { BtReplayTradeContext };
