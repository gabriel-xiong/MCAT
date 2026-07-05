# Sync demo script (OPTIONAL — not recorded)

**Status: NOT RECORDED** as of 2026-07-05. Use this only if you capture sync later;
graders should rely on the written merge rule + headless perf-bundle proof until then.

**Prerequisites:** AnkiDroid MCAT APK, desktop graded MSI, local Anki sync server
(or AnkiWeb), two profiles pointed at the same collection. See
[`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) and
[`RECORDING-RUNBOOK.md`](RECORDING-RUNBOOK.md) §D for full detail.

**Target length:** ~4 min (addendum to main demo; do not replace product walkthrough).

---

## Beat 1 — Setup (30 s)

[SAY] Memory reviews sync through **stock Anki collection sync**. Performance attempts
live in a **separate sidecar** and sync via an export/import bundle — different rules,
both documented.

[DO] Show phone + desktop on same collection name; note sync server URL on screen.

---

## Beat 2 — 10 + 10 offline (90 s)

[DO]

1. **Phone:** airplane mode ON → review **10 different cards** → note count **C_phone**.
2. **Desktop:** offline → review **10 other cards** → count **C_desktop**.
3. Reconnect both → **Sync** on phone, then desktop.

[SAY] After merge, revlog should have **C_phone + C_desktop** distinct rows — append-only
by review id, **none lost, none doubled**. This is stock Anki semantics.

[DO] Open Browse → sort by review time → count new rows (or show pre/post revlog count).

---

## Beat 3 — Same-card conflict winner (90 s)

[DO]

1. Pick one shared due card.
2. **Phone offline:** review it (e.g. Good) at time T1.
3. **Desktop offline:** review the **same card** (e.g. Hard) at time T2 > T1.
4. Sync both ways.

[SAY] Winner is **last-review-wins by `mtime`** — the later review’s scheduling state
survives; both revlog entries are kept. Rule is in `SYNC-CONFLICT-RULE.md`.

[DO] Show the card’s final interval/ease matches the **later** device.

---

## Beat 4 — Perf bundle (optional, 60 s)

[DO] Export perf bundle on phone → import on desktop → show attempt count increased;
re-import same file → count unchanged (idempotent uuid merge).

[SAY] Performance channel is proven headlessly in `undo-integrity-results.json`; this
beat is optional eye candy.

---

## If you never record this

Point graders to:

- [`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) — written §7b artifact
- [`artifacts/undo-integrity-results.json`](artifacts/undo-integrity-results.json) — 15/15 perf merge checks
- [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md) §GAPS — “no sync recording” listed explicitly
