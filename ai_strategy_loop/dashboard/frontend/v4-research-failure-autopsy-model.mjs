const FAILURE_LABELS = Object.freeze({
  MIN_POSITIVE_TOTAL_PROFIT_FOLDS: "양수 Fold 부족",
  COMBINED_AVG_PROFIT: "결합 평균 손익",
  COMBINED_TOTAL_PROFIT: "결합 총손익",
  MIN_TRADES_EACH_FOLD: "Fold 최소 거래수",
  MAX_MDD_EACH_FOLD: "MDD 상한",
});

function finite(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function round(value, digits = 2) {
  const factor = 10 ** digits;
  return Math.round((finite(value) + Number.EPSILON) * factor) / factor;
}

function failureAutopsy(analysis) {
  const candidates = Array.isArray(analysis?.candidates) ? analysis.candidates : [];
  const failureCounts = {};
  const exitMap = new Map();
  const familyMap = new Map();
  const folds = candidates.flatMap(candidate => Array.isArray(candidate.folds) ? candidate.folds : []);

  for (const candidate of candidates) {
    for (const failure of candidate.development_failures || []) {
      failureCounts[failure] = finite(failureCounts[failure]) + 1;
    }
    for (const exit of candidate.exits || []) {
      const key = String(exit.exit_kind || "UNKNOWN");
      const current = exitMap.get(key) || { exitKind: key, g0Count: 0, g1Count: 0, countDelta: 0, pnlDeltaKrw: 0 };
      exitMap.set(key, {
        exitKind: key,
        g0Count: current.g0Count + finite(exit.g0_count),
        g1Count: current.g1Count + finite(exit.g1_count),
        countDelta: current.countDelta + finite(exit.count_delta),
        pnlDeltaKrw: current.pnlDeltaKrw + finite(exit.pnl_delta_krw),
      });
    }
    const familyId = String(candidate.family_id || "UNKNOWN");
    const observed = (candidate.folds || []).some(fold => fold.g1_metrics_observed === true);
    const current = familyMap.get(familyId) || {
      familyId, candidateCount: 0, pairedPassCount: 0, developmentPassCount: 0,
      g0Trades: 0, g1Trades: 0, positiveFolds: 0, sumProfitPct: 0,
      observedCandidateCount: 0, maxMddPct: null,
    };
    const candidateMdd = observed ? finite(candidate.g1_max_fold_mdd_pct) : null;
    familyMap.set(familyId, {
      ...current,
      candidateCount: current.candidateCount + 1,
      pairedPassCount: current.pairedPassCount + (candidate.paired_falsification_pass === true ? 1 : 0),
      developmentPassCount: current.developmentPassCount + (candidate.development_rule_pass === true ? 1 : 0),
      g0Trades: current.g0Trades + finite(candidate.g0_total_trades),
      g1Trades: current.g1Trades + finite(candidate.g1_total_trades),
      positiveFolds: current.positiveFolds + finite(candidate.g1_positive_fold_count),
      sumProfitPct: current.sumProfitPct + (observed ? finite(candidate.g1_sum_total_profit_pct) : 0),
      observedCandidateCount: current.observedCandidateCount + (observed ? 1 : 0),
      maxMddPct: candidateMdd == null ? current.maxMddPct : Math.max(current.maxMddPct ?? candidateMdd, candidateMdd),
    });
  }

  const g0Trades = candidates.reduce((sum, row) => sum + finite(row.g0_total_trades), 0);
  const g1Trades = candidates.reduce((sum, row) => sum + finite(row.g1_total_trades), 0);
  const reduction = g0Trades - g1Trades;
  const failureRows = Object.entries(failureCounts)
    .map(([code, count]) => ({ code, label: FAILURE_LABELS[code] || code, count }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
  return {
    candidateCount: candidates.length,
    familyCount: familyMap.size,
    pairedPassCount: finite(analysis?.paired_pass_count),
    developmentPassCount: finite(analysis?.development_rule_pass_count),
    failureCounts,
    failureRows,
    folds: {
      total: folds.length,
      observed: folds.filter(row => row.g1_metrics_observed === true).length,
      unobserved: folds.filter(row => row.g1_metrics_observed !== true).length,
      positiveProfit: folds.filter(row => row.g1_metrics_observed === true && finite(row.g1_total_profit_pct) > 0).length,
      averageImproved: folds.filter(row => row.g1_metrics_observed === true && finite(row.avg_profit_pct_delta) > 0).length,
      mddOver15: folds.filter(row => row.g1_metrics_observed === true && finite(row.g1_mdd_pct) > 15).length,
    },
    trades: { g0: g0Trades, g1: g1Trades, reduction, reductionPct: g0Trades ? round(reduction / g0Trades * 100) : 0 },
    exits: [...exitMap.values()].map(row => ({ ...row, pnlDeltaKrw: round(row.pnlDeltaKrw, 0) })).sort((left, right) => left.exitKind.localeCompare(right.exitKind)),
    families: [...familyMap.values()].map(row => ({ ...row, sumProfitPct: row.observedCandidateCount ? round(row.sumProfitPct) : null, maxMddPct: row.maxMddPct == null ? null : round(row.maxMddPct) })).sort((left, right) => left.familyId.localeCompare(right.familyId)),
    candidates: candidates.map(row => ({
      candidateId: String(row.candidate_id || "UNKNOWN"),
      familyId: String(row.family_id || "UNKNOWN"),
      g1Trades: finite(row.g1_total_trades),
      positiveFolds: finite(row.g1_positive_fold_count),
      sumProfitPct: round(row.g1_sum_total_profit_pct),
      maxMddPct: round(row.g1_max_fold_mdd_pct),
      pairedPass: row.paired_falsification_pass === true,
      developmentPass: row.development_rule_pass === true,
      metricsObserved: (row.folds || []).some(fold => fold.g1_metrics_observed === true),
      failures: (row.development_failures || []).map(code => FAILURE_LABELS[code] || code),
    })),
  };
}

export { failureAutopsy };
