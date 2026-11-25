"""sahasrahbot.py must own the event loop.

Quart's ``app.run()`` blocks until shutdown and then closes the loop. Called from
``sahasrahbot.py`` it ran the whole process inside itself, so the lines after it
(the Sentry runtime gauges and the blocked-loop watchdog) never ran, and every
restart ended with ``RuntimeError: Event loop is closed`` (Sentry SAHASRAHBOT-2).
"""

import ast
import pathlib

ENTRY = pathlib.Path(__file__).resolve().parent.parent / "sahasrahbot.py"


def _calls(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            target = node.func.value
            yield (target.id if isinstance(target, ast.Name) else None), node.func.attr


def test_web_app_is_started_as_a_task_not_with_blocking_run():
    calls = set(_calls(ast.parse(ENTRY.read_text())))
    assert ("sahasrahbotapi", "run") not in calls
    assert ("sahasrahbotapi", "run_task") in calls


def test_runtime_gauges_and_watchdog_are_scheduled_before_the_loop_runs():
    source = ENTRY.read_text()
    run_at = source.index("loop.run_until_complete(api_task)")
    assert source.index("observability_runtime.start") < run_at
    assert source.index("observability_watchdog.start") < run_at
