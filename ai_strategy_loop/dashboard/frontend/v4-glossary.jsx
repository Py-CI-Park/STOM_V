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
    // v5.11.3 — 거버넌스 화면을 우리말로 바꾸면서 쓴 낱말을 여기서 한 번 더 정의한다.
    //   화면에서 본 표현과 사전의 표제어가 다르면 용어 탭이 무용지물이 된다.
    title: "거버넌스 화면 용어(우리말 ↔ 원어)",
    rows: [
      ["탐색 정책 (preset)", "이번 연구가 어떤 범위까지 조건식을 만들 수 있는지 정해 둔 기본 설정."],
      ["연구 시간대 (time window)", "연구 대상으로 삼는 장중 시간 구간. 이 밖의 거래는 집계하지 않는다."],
      ["최대 낙폭 한도 (MDD gate)", "이보다 깊게 물리면 점수와 무관하게 탈락하는 하드 기준."],
      ["하루 최소 거래 (trade gate)", "표본이 모자라면 탈락시키는 빈도 하드 기준."],
      ["생성 권한 (generation authority)", "지금 연구용 생성이 허용된 상태인지, 검토 전용인지."],
      ["연구 자료 묶음 (context pack)", "조건식을 만들기 전에 읽어야 하는 자료 묶음과 그 토큰 상한."],
      ["후보 묶음 (candidate pack)", "한 세대에서 만들어야 하는 후보 개수와 필수 기재 항목."],
      ["분석 카드 (analysis cards)", "원인·구간 기여·인사이트 점수를 담는 정형 분석 기록."],
      ["프롬프트 기록 (prompt receipts)", "무엇을 근거로 생성했는지 남기는 영수증. 승격 권한은 없다."],
      ["승격을 막는 항목 (promotion blockers)", "채워지기 전까지 실전 승격을 막는 조건 목록."],
      ["증거 상태 (evidence health)", "필수 증거가 있는지(있음/없음/필수) 한눈에 보는 집계."],
      ["참고용 점수 (advisory score)", "연구 비교용 점수. 이 점수만으로는 어떤 전략도 승격되지 않는다."],
      ["파생값", "백엔드가 발행하지 않았지만 발행된 값에서 계산해 보여주는 값(예: 연평균 수익률)."],
      ["미발행", "해당 값이 어디에도 발행되지 않은 상태. 0 이나 추정값으로 대체하지 않는다."],
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
