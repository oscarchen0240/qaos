import type { ReviewStatus } from "./api";

export const REVIEW_LABEL: Record<ReviewStatus, string> = { pending: "待審", reviewed: "已審", returned: "退回" };
export const REVIEW_CLASS: Record<ReviewStatus, string> = { pending: "warn", reviewed: "ok", returned: "danger" };
export const REVIEW_STATUSES = Object.keys(REVIEW_LABEL) as ReviewStatus[];
