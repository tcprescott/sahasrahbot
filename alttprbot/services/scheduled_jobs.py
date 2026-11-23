"""Every periodic job SahasrahBot runs, and how often.

``sahasrahbot.py`` calls ``register_jobs`` on the process's ``Scheduler`` before
starting it. Add new periodic work here, not as a ``discord.ext.tasks`` loop in a cog:
the job does the work and publishes events, and a subscriber does any Discord output.
"""
from typing import Optional

import config
from alttprbot.services import daily, tournament_jobs
from alttprbot.services.scheduler import Gate, Scheduler

MINUTE = 60
HOUR = 60 * MINUTE


def _tournament_interval(seconds: float) -> float:
    # Tournament jobs run every 15 seconds in DEBUG, as the old task loops did.
    return 15 if config.DEBUG else seconds


def register_jobs(scheduler: Scheduler, tournament_ready: Optional[Gate] = None) -> None:
    """Register every periodic job.

    ``tournament_ready`` gates the tournament jobs: their event config
    (``TournamentConfig``) still holds the Discord guild and channels, so they can't
    start until the Discord bot is ready. ``sahasrahbot.py`` passes that wait.
    """
    scheduler.add_interval_job('daily.check_for_new_daily', daily.check_for_new_daily, seconds=5 * MINUTE)

    scheduler.add_interval_job('tournament.create_races', tournament_jobs.create_races,
                               seconds=_tournament_interval(5 * MINUTE), wait_for=tournament_ready)
    scheduler.add_interval_job('tournament.week_races', tournament_jobs.week_races,
                               seconds=_tournament_interval(15 * MINUTE), wait_for=tournament_ready)
    scheduler.add_interval_job('tournament.record_races', tournament_jobs.record_races,
                               seconds=_tournament_interval(15 * MINUTE), wait_for=tournament_ready)
    scheduler.add_interval_job('tournament.find_races_with_bad_discord', tournament_jobs.find_races_with_bad_discord,
                               seconds=_tournament_interval(4 * HOUR), wait_for=tournament_ready)
