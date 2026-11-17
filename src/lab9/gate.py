"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    rows = pr.get("rows") or []
    man = pr.get("manifest", {})
    spec_ids = [m["id"] for m in spec.get("metrics", [])]

    # 1. Giá trị metric NaN/inf: so sánh `nan < min` luôn False nên gate ngây thơ sẽ cho qua.
    for k, v in (pr.get("metrics") or {}).items():
        if isinstance(v, float) and not math.isfinite(v):
            problems.append(f"metric {k} is {v} (NaN/inf)")

    # 2. Số dòng phải bằng items x seeds, và không có dòng trùng (item, seed).
    want_rows = man.get("items", 0) * len(man.get("seeds", []))
    if len(rows) != want_rows:
        problems.append(f"{len(rows)} rows but manifest says {man.get('items')} items x {len(man.get('seeds', []))} seeds = {want_rows}")
    keys = [(r.get("item_id"), r.get("seed")) for r in rows]
    dup = sorted({str(k) for k in keys if keys.count(k) > 1})
    if dup:
        problems.append(f"duplicate (item, seed) rows: {', '.join(dup[:5])}")

    # 3. Tập (item, seed) của PR phải trùng baseline: không chọn seed/item đẹp.
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base.get("rows") or []}
    if set(keys) != base_keys:
        miss, extra = base_keys - set(keys), set(keys) - base_keys
        problems.append(f"(item, seed) set differs from baseline: {len(miss)} missing, {len(extra)} extra")
    bm = base.get("manifest", {})
    if (man.get("items"), sorted(man.get("seeds", []))) != (bm.get("items"), sorted(bm.get("seeds", []))):
        problems.append("manifest items/seeds differ from baseline")

    # 4. Grader crash: evaluator_failures, hoặc dòng thiếu giá trị cho metric đã chấm.
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s): {pr['evaluator_failures'][0]}")
    base_row0 = (base.get("rows") or [{}])[0]
    graded = [i for i in spec_ids if i in base_row0 or (rows and i in rows[0])]
    for mid in graded:
        n_none = sum(1 for r in rows if r.get(mid) is None)
        if n_none:
            problems.append(f"{n_none} row(s) have no value for graded metric {mid} (crashed grader?)")

    # 5. Metric trong report phải khớp tính lại từ rows (không sửa tay số tổng).
    for m in spec.get("metrics", []):
        mid = m["id"]
        if mid not in graded or not rows:
            continue
        vals = [r[mid] for r in rows if r.get(mid) is not None]
        if not vals:
            continue
        got = (pr.get("metrics") or {}).get(mid)
        want = float(sum(vals)) if m.get("kind") == "safety" else round(sum(vals) / len(vals), 4)
        if not isinstance(got, (int, float)) or isinstance(got, bool) or not math.isfinite(got) or abs(got - want) > 1e-3:
            problems.append(f"metric {mid} reports {got} but rows give {want}")
    if "pass_rate" in graded and rows:
        by_item: dict = {}
        for r in rows:
            by_item.setdefault(r["item_id"], []).append(bool(r.get("pass_rate")))
        for k in spec.get("pass_k", []):
            for name, fn in (("pass_at", stats.pass_at_k), ("pass_hat", stats.pass_hat_k)):
                got = (pr.get("metrics") or {}).get(f"{name}_{k}")
                if got is None or min(len(v) for v in by_item.values()) < k:
                    continue
                est = [fn(len(v), sum(v), k) for v in by_item.values()]
                want = round(sum(est) / len(est), 4)
                if not isinstance(got, (int, float)) or not math.isfinite(got) or abs(got - want) > 1e-3:
                    problems.append(f"metric {name}_{k} reports {got} but rows give {want}")

    # 6. Slice tag của mỗi item phải đồng nhất và trùng baseline (đổi nhãn để né slice gate).
    def tags(rs: list) -> dict:
        out: dict = {}
        for r in rs:
            out.setdefault(r.get("item_id"), set()).add(tuple(sorted(r.get("slices") or [])))
        return out
    pt, bt = tags(rows), tags(base.get("rows") or [])
    for item, forms in pt.items():
        if len(forms) > 1:
            problems.append(f"item {item} has inconsistent slice tags across seeds")
        elif item in bt and forms != bt[item]:
            problems.append(f"item {item} slice tags differ from baseline: {sorted(forms)} vs {sorted(bt[item])}")

    # 7. Ratchet: cùng eval-set version thì ngưỡng chỉ được chặt hơn.
    if base_spec is not None and base_spec.get("eval_set_version") == spec.get("eval_set_version"):
        problems += _ratchet(spec, base_spec)
    return problems


def _ratchet(spec: dict, base_spec: dict) -> list[str]:
    out: list[str] = []

    def looser(name: str, new: dict, old: dict) -> None:
        if "min" in old and ("min" not in new or new["min"] < old["min"]):
            out.append(f"{name}: min loosened {old['min']} -> {new.get('min')}")
        if "max" in old and ("max" not in new or new["max"] > old["max"]):
            out.append(f"{name}: max loosened {old['max']} -> {new.get('max')}")
        if "max_increase" in old and ("max_increase" not in new or new["max_increase"] > old["max_increase"]):
            out.append(f"{name}: max_increase loosened {old['max_increase']} -> {new.get('max_increase')}")
        if old.get("no_significant_drop") and not new.get("no_significant_drop"):
            out.append(f"{name}: no_significant_drop dropped")

    new_m = {m["id"]: m for m in spec.get("metrics", [])}
    for old in base_spec.get("metrics", []):
        new = new_m.get(old["id"])
        if new is None:
            out.append(f"metric {old['id']} removed")
            continue
        if old.get("blocking") and not new.get("blocking"):
            out.append(f"metric {old['id']} no longer blocking")
        looser(f"metric {old['id']}", new.get("threshold") or {}, old.get("threshold") or {})
    new_s = {x["name"]: x for x in spec.get("slices") or []}
    for old in base_spec.get("slices") or []:
        new = new_s.get(old["name"])
        if new is None:
            out.append(f"slice {old['name']} removed")
            continue
        if new.get("metric") != old.get("metric"):
            out.append(f"slice {old['name']} metric changed {old.get('metric')} -> {new.get('metric')}")
        if old.get("blocking") and not new.get("blocking"):
            out.append(f"slice {old['name']} no longer blocking")
        looser(f"slice {old['name']}", new, old)
    if not set(base_spec.get("seeds") or []) <= set(spec.get("seeds") or []):
        out.append("seeds shrunk versus base spec")
    return out


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        sid = f"slice:{name}/{metric}"
        verdict, note = "ok", ""
        if not a:
            verdict, note = "fail", "no rows in slice"
            val = float("nan")
        else:
            val = sum(a.values()) / len(a)
            if "min" in sl and val < sl["min"]:
                verdict = "fail"
            keys = sorted(set(a) & set(b))
            if sl.get("no_significant_drop") and keys:
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                                   n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"
        is_blocking = sl.get("blocking", True)
        if verdict != "ok" and is_blocking:
            blocked.append(sid)
        label = "ok" if verdict == "ok" else ("BLOCK" if is_blocking else "warn")
        th = json.dumps({k: v for k, v in sl.items() if k in ("min", "no_significant_drop")})
        lines.append(f"  {sid:<34} {val:<8.4f} n={len(a):<3} {th:<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
