#!/usr/bin/env python3
"""Bucket kill-test per-instance results into: clean-resolve / fixed-but-broke / not-fixed."""
import json, glob, os, sys

RUN_ID = "kt_openhands_opus45"
LOG_DIR = os.path.join("logs", "run_evaluation", RUN_ID)
sel = {r["instance_id"]: r for r in json.load(open("kt_selection.json"))}
want = [json.loads(l)["instance_id"] for l in open("kt_preds.jsonl") if l.strip()]

def find_report(iid):
    hits = glob.glob(os.path.join(LOG_DIR, "*", iid, "report.json"))
    return hits[0] if hits else None

clean, broke, notfixed, noeval = [], [], [], []
for iid in want:
    rp = find_report(iid)
    if not rp:
        noeval.append((iid, "no report.json (build/run error)"))
        continue
    data = json.load(open(rp))
    rec = data.get(iid, data)
    ts = rec.get("tests_status", {})
    f2p_fail = ts.get("FAIL_TO_PASS", {}).get("failure", [])
    f2p_ok   = ts.get("FAIL_TO_PASS", {}).get("success", [])
    p2p_fail = ts.get("PASS_TO_PASS", {}).get("failure", [])
    applied  = rec.get("patch_successfully_applied", None)
    if not f2p_ok and not f2p_fail:
        # no FAIL_TO_PASS ran at all (e.g. patch didn't apply) -> not fixed
        notfixed.append((iid, f"no FAIL_TO_PASS executed (patch_applied={applied})"))
    elif f2p_fail:
        notfixed.append((iid, f"{len(f2p_fail)} FAIL_TO_PASS still failing"))
    elif p2p_fail:
        broke.append((iid, p2p_fail))
    else:
        clean.append(iid)

def tag(iid): return f"{iid} [{sel.get(iid,{}).get('version','?')}, submission={sel.get(iid,{}).get('submission_bucket','?')}]"

print("="*72)
print(f"KILL TEST — OpenHands + Claude Opus 4.5  |  {len(want)} instances, harness re-run")
print("="*72)
print(f"\n(a) CLEAN RESOLVE  (all FAIL_TO_PASS pass, all PASS_TO_PASS pass): {len(clean)}")
for i in clean: print("     ", tag(i))
print(f"\n(b) FIXED-BUT-BROKE (all FAIL_TO_PASS pass, >=1 PASS_TO_PASS FAILS): {len(broke)}")
for i, fails in broke:
    print("     ", tag(i))
    for t in fails: print("           BROKE PASS_TO_PASS:", t)
print(f"\n(c) NOT FIXED  (FAIL_TO_PASS still failing): {len(notfixed)}")
for i, why in notfixed: print("     ", tag(i), "->", why)
if noeval:
    print(f"\n[!] NOT EVALUABLE (set aside): {len(noeval)}")
    for i, why in noeval: print("     ", tag(i), "->", why)
print("\n" + "-"*72)
print(f"TOTAL: clean={len(clean)}  fixed-but-broke={len(broke)}  not-fixed={len(notfixed)}  noeval={len(noeval)}  (sum={len(clean)+len(broke)+len(notfixed)+len(noeval)}/{len(want)})")
print("Regression phenomenon present?", "YES" if broke else "no cases in this sample")
