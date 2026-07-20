/* v4-glossary.jsx — v5.6.1: 종합 '용어' 탭(설정 뒤). Metric glossary + 연구실 용어를
 *   위키처럼 한 곳에서 관리(사장님 지시). 읽기 전용 정적 지식 표면.
 */
import { ResearchGlossaryPanel } from "./glossary.jsx";

const _V4G_SECTIONS = [
  {
    title: "연구실 분석 용어",
    rows: [
      ["엣지(Edge Ratio)", "조건이 실제로 유리했던 구간의 비율 — 시간대·시총·회전율 축으로 승률/기대값을 본다."],
      ["변수 중요도", "성과 차이를 크게 만든 입력 변수 — 상관·회귀 기반 순위."],
      ["상관관계", "변수와 결과가 같이 움직인 정도(spearman/pearson). 절대값이 클수록 관계가 강함."],
      ["변수 조합 후보", "두 변수의 상호작용(interaction) 중 연구 가치가 높은 쌍."],
      ["검증·안정성", "후보를 다른 기간·조건(OOS/워크포워드)으로 다시 확인하는 단계."],
    ],
  },
  {
    title: "백테스트 지표",
    rows: [
      ["graded score(적합도)", "수익·MDD·거래수 게이트 통과 정도를 등급화한 채점 점수. 게이트 기준 이상이면 통과."],
      ["MDD(최대 낙폭)", "고점 대비 최대 하락률(%). 낮을수록 안전. run 게이트 상한이 적용된다."],
      ["Calmar", "CAGR ÷ MDD — 위험조정 수익. 높을수록 우수."],
      ["우상향 R²", "누적수익 곡선의 직선 적합도(0~1). 1에 가까울수록 꾸준한 우상향."],
      ["Payoff(손익비)", "평균 이익 ÷ |평균 손실|. 1 초과일수록 우수."],
      ["일평균거래", "거래수 ÷ 거래일수 — 빈도 게이트의 주 기준."],
      ["동시보유(max hold)", "동시에 보유한 최대 종목 수 — 분산 진입의 근사(사람 기준 6~12)."],
      ["Give-back%", "최대 이익(MFE) 도달 후 반납한 비율. 낮을수록 청산이 우수."],
      ["MAE / MFE", "진입 후 최대 역행/순행 폭 — 손절·익절 규칙 연구의 원재료."],
    ],
  },
  {
    title: "파이프라인 · 거버넌스",
    rows: [
      ["세대(gen)", "생성→백테스트→채점→부검 1사이클의 산출물(조건식 1쌍)."],
      ["게이트", "score·MDD·거래수 하드 기준 — 통과해야 우승 후보 자격."],
      ["부검(autopsy)", "실패/손실 구간의 원인 분석 — 다음 세대 프롬프트로 환류."],
      ["홀드아웃", "학습에 안 쓴 기간으로 진행하는 졸업검사(과적합 방어)."],
      ["human 승인 게이트", "우승 조건식의 운영 export 는 반드시 사람 승인 절차를 거친다(자동 승격 금지)."],
      ["performance_proved=false", "통제된 A/B 증거 전까지 성능(수익) 주장을 하지 않는다는 시스템 불변 원칙."],
    ],
  },
];

function V4GlossaryTab() {
  return (
    <section className="v4-glossary" aria-labelledby="v4-glossary-heading">
      <h2 id="v4-glossary-heading" className="panel-hd-title">용어 · 종합 위키</h2>
      <div className="v4g-grid">
        {_V4G_SECTIONS.map(sec => (
          <div className="panel" key={sec.title}>
            <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>{sec.title}</div></div>
            <div className="panel-bd">
              {sec.rows.map(([k, v]) => (
                <div className="v4g-row" key={k}>
                  <b className="v4g-term">{k}</b>
                  <span className="v4g-desc">{v}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
        <div className="panel">
          <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>연구 기준 · 게이트 용어(정본)</div></div>
          <div className="panel-bd">
            <ResearchGlossaryPanel />
          </div>
        </div>
      </div>
    </section>
  );
}

Object.assign(window, { V4GlossaryTab });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4GlossaryTab };
