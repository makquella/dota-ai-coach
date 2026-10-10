// «Стан операцій» in the developer section: GET /operations/health
// (backend/app/operations_health.py) as a few lines — background queues, saving
// the finished match, the live GSI path and how fresh the data are — plus the
// warnings it names. The pure part is UMD so test/ops-health.test.js runs it;
// the copy lives in app-texts.js (`ops*`, `opsWarn_<code>`).
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.OpsHealth = api;
  }
})(typeof self !== "undefined" ? self : this, function () {
  const num = (value) => (typeof value === "number" && Number.isFinite(value) ? value : null);
  const secs = (value) => Math.round(num(value) ?? 0);
  // "12:04" from an ISO time, local clock; "" when missing or broken.
  const clock = (iso) => {
    const date = iso ? new Date(iso) : null;
    return date && !Number.isNaN(date.getTime())
      ? `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`
      : "";
  };
  const later = (first, second) => Boolean(first) && (!second || String(first) > String(second));

  function queueLine(queue, tr) {
    const q = queue || {};
    if (q.running) {
      return tr("opsQueueRunning", q.running_kind || "job", secs(q.running_for_s), q.queued || 0);
    }
    if (q.queued) {
      return num(q.oldest_due_s) != null ? tr("opsQueueWaiting", q.queued, secs(q.oldest_due_s)) : tr("opsQueueLater", q.queued, secs(q.next_in_s));
    }
    return q.failed ? tr("opsQueueIdleFailed", q.completed || 0, q.failed, clock(q.last_failed_at)) : tr("opsQueueIdle", q.completed || 0);
  }

  function finishLine(finish) {
    const f = finish || {};
    return { pending: f.pending_finishes || 0, saved: clock(f.last_ack_at), failed: later(f.last_ack_error_at, f.last_ack_at) };
  }

  // [{key, value, state}] for the <dl>; state "bad" marks a line with a warning.
  function rows(health, tr) {
    const h = health || {};
    const warn = new Set(h.warnings || []);
    const queues = h.queues || {};
    const finish = finishLine(h.match_finish);
    const total = (h.live_path || {})["gsi.total"] || {};
    const persistence = (h.live_path || {})["gsi.persistence"] || {};
    const fresh = h.freshness || {};
    return [
      { key: "opsJobs", value: queueLine(queues.jobs, tr), state: [...warn].some((w) => w.startsWith("jobs_")) ? "bad" : "" },
      { key: "opsAi", value: queueLine(queues.ai_jobs, tr), state: [...warn].some((w) => w.startsWith("ai_jobs_")) ? "bad" : "" },
      {
        key: "opsMatch",
        value: finish.pending ? tr("opsMatchPending", finish.pending) : finish.saved ? tr("opsMatchSaved", finish.saved) : tr("opsMatchNone"),
        state: warn.has("match_not_saved") || warn.has("recovery_write_failed") ? "bad" : finish.saved && !finish.pending ? "good" : ""
      },
      {
        key: "opsGsi",
        value: total.count
          ? tr("opsGsiTimes", total.count, num(total.p50_ms), num(total.p95_ms), persistence.failed || 0)
          : tr("opsGsiNone"),
        state: warn.has("gsi_slow") || warn.has("gsi_persistence_failed") ? "bad" : ""
      },
      {
        key: "opsData",
        value: tr("opsDataLine", fresh.sync_state || "", clock(fresh.sync_at), fresh.builds_generated || "", num(fresh.builds_age_days)),
        state: warn.has("sync_failed") || warn.has("builds_stale") ? "bad" : ""
      }
    ];
  }

  // The warnings in words; an unknown code (a newer backend) stays as it is.
  function warningTexts(health, trOr) {
    return ((health || {}).warnings || []).map((code) => trOr(`opsWarn_${code}`, code));
  }

  return { rows, warningTexts, queueLine, clock };
});
