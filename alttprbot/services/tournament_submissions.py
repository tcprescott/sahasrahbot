"""Race settings submission: the form a tournament sends its players before a race,
and handing the answers to that tournament's ``process_submission_form``.

A tournament class offers a form by returning a list from ``submission_form``:
``[{'key': 'preset', 'label': 'Preset', 'settings': {'open': 'Open', ...}}, ...]``.
"""

from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.tournaments import TOURNAMENT_DATA, fetch_tournament_handler


async def _form(event: str) -> list:
    if event not in TOURNAMENT_DATA:
        raise NotFoundError(f"There's no tournament called {event}.")
    tournament = await TOURNAMENT_DATA[event].get_config()
    form = tournament.submission_form
    if not isinstance(form, list) or not form:
        raise NotFoundError(f"{event} doesn't take settings submissions.")
    return form


async def get_form(event: str) -> dict:
    form = await _form(event)
    return {
        'event': event,
        'fields': [
            {
                'key': field['key'],
                'label': field['label'],
                'options': [{'value': str(k), 'label': str(v)} for k, v in field['settings'].items()],
            }
            for field in form
        ],
    }


async def submit(event: str, episode_id: int, settings: dict[str, str], submitted_by: str) -> dict:
    form = await _form(event)
    for field in form:
        choice = settings.get(field['key'])
        if choice is None or choice not in {str(k) for k in field['settings']}:
            raise InvalidInputError(f"Pick a value for {field['label']}.")

    payload = {**{f['key']: settings[f['key']] for f in form}, 'event': event, 'episodeid': str(episode_id)}
    try:
        tournament_race = await fetch_tournament_handler(event, episode_id)
        await tournament_race.process_submission_form(payload, submitted_by=submitted_by)
    except Exception as e:
        raise InvalidInputError(f"We couldn't save those settings: {e}") from e
    return {'event': event, 'episode_id': episode_id, 'versus': tournament_race.versus}
