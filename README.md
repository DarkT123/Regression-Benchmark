# SWE-bench Regression Re-scoring

**How often do coding agents break working code while fixing a bug?**

SWE-bench leaderboards rank agents by resolve rate: did the agent fix the reported issue? The harness also runs `PASS_TO_PASS` tests (tests that passed before the change and should still pass after), but the outcome is collapsed into a single pass/fail and never surfaced in rankings.

That hides two things:

1. **A safety cost.** An agent can fix the reported bug and silently break unrelated working functionality. The leaderboard shows only that the instance was "unresolved".
2. **A hidden competence.** Some instances counted as failures are not failures at all. The bug *was* fixed; a regression test tripped, and the instance was binned with genuine failures.

This repository re-scores already-published agent patches to separate those cases and report the regression rate directly.

## What this is (and is not)

This is **not a new benchmark**. No new tasks, environments or harness were built. It is a **re-analysis** of existing SWE-bench Verified instances using published patches from an existing leaderboard submission, scored through the official harness with the per-test results read more carefully.

## Method

- **Dataset:** SWE-bench Verified, Django instances only.
- **Patches:** published predictions from the OpenHands + Claude Opus 4.5 submission, retrieved from the public `swe-bench-submissions` S3 bucket referenced in the submission's `metadata.yaml`.
- **Harness:** `swebench` 4.1.0, official evaluation harness.
- **Harness validation:** gold-patch validation run first. 5/5 gold patches resolved, 0 unresolved. This confirms the harness measures correctly before any model patch is scored.
- **Sample:** 25 randomly selected Django Verified instances (seed 42), spanning Django 3.0 to 5.0. The submission resolved 18/25 (72%), consistent with its published ~80% Django rate, confirming the sample is not weighted toward failures.
- **Execution:** serialised (`--max_workers 1`), x86_64 images under emulation on Apple Silicon.

## Scoring

Each (model, instance) pair is sorted into one of three buckets:

| Bucket | FAIL_TO_PASS | PASS_TO_PASS | Meaning |
|---|---|---|---|
| **(a) clean resolve** | all pass | all pass | Bug fixed, nothing broken |
| **(b) fixed-but-broke** | all pass | ≥1 fails | Bug fixed, working code broken |
| **(c) not fixed** | fails | any | Bug not fixed |

Bucket (b) is invisible on the leaderboard: SWE-bench marks these instances "unresolved", identical to bucket (c).

**Headline metric:** regression rate among resolves = `b / (a + b)`. Of the bugs the agent appeared to fix, the share where it broke something else.

## Results

| Bucket | Count (n=25) |
|---|---|
| (a) clean resolve | 18 |
| (b) fixed-but-broke | 2 |
| (c) not fixed | 5 |

**Regression rate among resolves: 10%** (2 of 20 apparent fixes broke a previously-passing test).

The two fixed-but-broke instances in this sample were `django-11734` (broke 4 `queries.tests` tests, all raising `ValueError: This queryset contains a reference to an outer query...`) and `django-12273` (broke `test_issue_6755` with `AssertionError: 2 != 1`). Both were re-run and confirmed deterministic.

## Verified case studies

Both cases below were manually inspected and confirmed as genuine regressions, not flaky tests.

### django-14170: a loud break (9 tests)

`FAIL_TO_PASS` 2/2 pass. `PASS_TO_PASS` 67 pass / **9 fail**.

The patch changed `YearLookup` / `Extract year` and removed the BETWEEN-filter indexing optimisation. Broken tests cluster in a single feature area across two test classes:

- `test_extract_year_func`, `test_extract_year_greaterthan_lookup`, `test_extract_year_lessthan_lookup`, `test_trunc_date_func` (`DateFunctionTests`)
- the same three `extract_year` tests plus `test_trunc_ambiguous_and_invalid_times` (`DateFunctionWithTimeZoneTests`)

The clustering is itself evidence of a real regression: flaky failures scatter across unrelated tests, whereas every test touching the modified behaviour failed together.

### django-14053: a quiet break (1 test)

`FAIL_TO_PASS` 1/1 pass. `PASS_TO_PASS` 30 pass / **1 fail**.

`test_post_processing_failure` fails deterministically with `AssertionError: Exception not raised`. The patch's change to `HashedFilesMixin.post_process()` swallowed the error-signalling path, so a failure that should raise an exception now passes silently.

This is the more instructive case. The fix works, and error reporting quietly stopped working. A thin test net would miss it entirely.

## Caveats

Read these before citing any number here.

- **Small sample.** n=25, single repository (Django), single agent. The rate is directional, not definitive.
- **Lower bound.** Scoring uses the `PASS_TO_PASS` set SWE-bench ships, which is thin and somewhat arbitrary. A wider regression net would catch more breakage and push the rate up. The true rate is at least this.
- **Not generalisable across repos.** Django has an unusually large, mature test suite. Regression rates elsewhere may differ, and that variation would itself be worth measuring.
- **Coverage ceiling.** A regression is only detectable if a test covers the broken behaviour. Breakage in untested code is invisible here, exactly as it is to CI.
- **Modified harness.** See below.

## Reproducing

The harness was run with one local modification. `swebench/harness/test_spec/python.py` was patched to support a `SWEBENCH_GIT_MIRROR` environment variable, which rewrites `github.com` clone URLs to a local `git daemon` mirror. This was necessary because both network paths to GitHub were unreliable from inside the containers in this environment (an HTTP proxy dropped large clones, and the direct route failed the TLS handshake). The patch is opt-in and inert when the variable is unset. It affects only where the repository is cloned from, not what is cloned or how it is scored.

- Patch: `patches/swebench-git-mirror.patch`
- Bucketing: `kt_bucket.py` reads each instance's `report.json` `tests_status` and emits the three bucket counts.
- Results: `results/` contains the per-instance summary JSON.

## Prior work

The observation that regression behaviour goes unreported is not novel. SWE Atlas (Scale AI) makes zero pass-to-fail regressions a hard requirement in its refactoring benchmark, and TDAD notes that the SWE-bench harness executes `PASS_TO_PASS` tests but does not surface the results in leaderboard rankings.

What is contributed here is narrow: the regression rate on **bug-fix** tasks, reported as a standalone comparative metric, computed cheaply from already-published patches with no model inference.

## Licence

MIT. Built on [SWE-bench](https://github.com/SWE-bench/SWE-bench) (MIT). Patches are from the OpenHands + Claude Opus 4.5 leaderboard submission. Django is the property of the Django Software Foundation.
