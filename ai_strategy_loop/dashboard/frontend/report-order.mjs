export function reportTimestamp(report) {
  const source = report && typeof report === "object" ? report : {};
  const dated = Date.parse(source.generated_at || source.date || "");
  if (Number.isFinite(dated)) return dated;
  const mtime = Number(source.mtime);
  if (!Number.isFinite(mtime)) return 0;
  return mtime < 1_000_000_000_000 ? mtime * 1000 : mtime;
}

export function sortReportsNewest(reports) {
  return (Array.isArray(reports) ? reports : []).slice().sort((a, b) => {
    const delta = reportTimestamp(b) - reportTimestamp(a);
    return delta || String(a?.path || "").localeCompare(String(b?.path || ""));
  });
}
