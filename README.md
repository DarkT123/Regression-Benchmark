SWE-bench Regression Evaluator

A scoring layer for SWE-bench that surfaces a metric the leaderboard discards. Test to see what agent breaks when they fix something. 


SWE-bench already runs two sets of tests per instance:


FAIL_TO_PASS — should start failing and pass once the bug is fixed
PASS_TO_PASS — already passing, and should stay passing


The leaderboard collapses both into one bit: resolved, or not. So two very different outcomes get the same label:


the agent failed to fix the bug
the agent fixed the bug and broke working code doing it


This evaluator separates them and reports the second as its own number.
