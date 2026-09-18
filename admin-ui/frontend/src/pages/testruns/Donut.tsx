import type { RunCounts } from "@/lib/api";

export const RESULT_LABEL: Record<string, string> = { pass: "Pass", fail: "Fail", blocked: "Blocked", skipped: "Skipped", untested: "Untested" };
export const RESULT_COLOR: Record<string, string> = { pass: "var(--ok)", fail: "var(--danger)", blocked: "var(--warn)", skipped: "var(--violet)", untested: "var(--surface-3)" };
const ORDER = ["pass", "fail", "blocked", "skipped", "untested"] as const;

/** 純 SVG 甜甜圈：結果分布＋中間通過率。reduced-motion 下無動畫。 */
export function Donut({ counts, size = 120, stroke = 14 }: { counts: RunCounts; size?: number; stroke?: number }) {
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;
  const segs = ORDER.map((k) => {
    const v = counts[k];
    const len = counts.total ? (v / counts.total) * circ : 0;
    const seg = { k, v, len, offset };
    offset += len;
    return seg;
  });
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`通過率 ${counts.pass_rate}%，${ORDER.map((k) => `${RESULT_LABEL[k]} ${counts[k]}`).join("，")}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
      {segs.filter((s) => s.len > 0).map((s) => (
        <circle key={s.k} cx={size / 2} cy={size / 2} r={r} fill="none" stroke={RESULT_COLOR[s.k]} strokeWidth={stroke}
          strokeDasharray={`${s.len} ${circ - s.len}`} strokeDashoffset={-s.offset} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      ))}
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central" fill="var(--text)" style={{ fontFamily: "var(--font-mono)", fontSize: size * 0.2, fontWeight: 600 }}>{counts.pass_rate}%</text>
      <text x="50%" y={size / 2 + size * 0.17} textAnchor="middle" fill="var(--text-faint)" style={{ fontSize: size * 0.085 }}>passed</text>
    </svg>
  );
}

export function Legend({ counts }: { counts: RunCounts }) {
  return (
    <div className="legend">
      {ORDER.map((k) => (
        <div key={k} className="legend-row">
          <span className="legend-dot" style={{ background: RESULT_COLOR[k] }} />
          <span className="mono" style={{ minWidth: 28, textAlign: "right" }}>{counts[k]}</span>
          <span>{RESULT_LABEL[k]}</span>
          <span className="faint mono" style={{ marginLeft: "auto" }}>{counts.total ? Math.round((counts[k] / counts.total) * 100) : 0}%</span>
        </div>
      ))}
    </div>
  );
}

export function ProgressBar({ counts }: { counts: RunCounts }) {
  return (
    <div className="run-progress" title={`${counts.done} / ${counts.total} 已執行`}>
      {ORDER.filter((k) => k !== "untested").map((k) => counts[k] > 0 && <span key={k} style={{ width: `${(counts[k] / Math.max(1, counts.total)) * 100}%`, background: RESULT_COLOR[k] }} />)}
    </div>
  );
}
