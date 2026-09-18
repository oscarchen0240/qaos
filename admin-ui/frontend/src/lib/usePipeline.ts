import { useEffect, useState } from "react";
import { api, type PipelineSnapshot } from "./api";

/**
 * SSE 訂閱 pipeline 快照。伺服器每 20 秒會主動收掉連線、瀏覽器自動重連（這是正常的，不算錯誤）；
 * 只有在完全連不上（從未收到資料、或重連持續失敗超過 15 秒）時才退回 5 秒輪詢。
 */
export function usePipeline(session: string | null) {
  const [snap, setSnap] = useState<PipelineSnapshot | null>(null);
  const [mode, setMode] = useState<"sse" | "poll" | "connecting">("connecting");
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    let poll: number | undefined;
    let fallbackTimer: number | undefined;
    let gotData = false;
    const qs = session ? `?session=${encodeURIComponent(session)}` : "";

    const fetchOnce = () => api.get<PipelineSnapshot>(`/api/pipeline/state${qs}`)
      .then((s) => { if (alive) { setSnap(s); setError(null); } })
      .catch((e) => alive && setError(e.message));

    const startPoll = () => {
      if (poll) return;
      setMode("poll");
      fetchOnce();
      poll = window.setInterval(fetchOnce, 5000);
    };

    if (typeof EventSource === "undefined") { startPoll(); return () => { alive = false; if (poll) clearInterval(poll); }; }

    const es = new EventSource(`/api/pipeline/stream${qs}`);
    es.addEventListener("state", (e) => {
      if (!alive) return;
      gotData = true;
      if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = undefined; }
      setSnap(JSON.parse((e as MessageEvent).data)); setMode("sse"); setError(null);
    });
    es.addEventListener("ping", () => { if (fallbackTimer) { clearTimeout(fallbackTimer); fallbackTimer = undefined; } });
    es.onopen = () => { if (alive && gotData) setMode("sse"); };
    es.onerror = () => {
      if (!alive) return;
      if (es.readyState === EventSource.CLOSED || !gotData) {
        // 從未成功過或被判定為致命錯誤 → 放棄 SSE，改輪詢
        es.close(); startPoll(); return;
      }
      // 伺服器 20 秒自動收線 → 瀏覽器會自動重連；若 15 秒內沒再收到資料就退回輪詢
      setMode("connecting");
      if (!fallbackTimer) fallbackTimer = window.setTimeout(() => { if (alive && es.readyState !== EventSource.OPEN) { es.close(); startPoll(); } }, 15000);
    };

    return () => { alive = false; es.close(); if (poll) clearInterval(poll); if (fallbackTimer) clearTimeout(fallbackTimer); };
  }, [session, tick]);

  return { snap, mode, error, reconnect: () => setTick((t) => t + 1), setSnap };
}
