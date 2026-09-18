import type { KeyboardEvent, MouseEvent } from "react";

/** 讓非 button 元素（tr / div / a）可用鍵盤操作：role=button、可 Tab、Enter/Space 觸發 */
export function clickable(onClick: (e?: MouseEvent | KeyboardEvent) => void, label?: string) {
  return {
    role: "button" as const,
    tabIndex: 0,
    "aria-label": label,
    onClick,
    onKeyDown: (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(e); }
    },
  };
}
