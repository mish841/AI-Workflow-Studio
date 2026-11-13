import type { DisplayStatus } from "../types";
import { DISPLAY_STATUS_LABELS } from "../lib/assessment";

export function StatusBadge({ status }: { status: DisplayStatus }) {
  return (
    <span className={`status status-${status}`}>
      <span className="status-dot" aria-hidden="true" />
      {DISPLAY_STATUS_LABELS[status]}
    </span>
  );
}
