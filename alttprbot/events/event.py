"""The :class:`Event` base class every published event derives from."""

import dataclasses
from datetime import datetime, timezone
from typing import ClassVar


@dataclasses.dataclass(frozen=True, kw_only=True)
class Event:
    """An immutable record of something that happened.

    Subclasses are frozen dataclasses with a class-level ``name`` in
    ``object.verb`` form (``race.status_changed``). Fields hold plain data only:
    ids, strings, numbers, datetimes, lists and dicts. Never put an ORM row, a
    ``discord`` object or a racetime handler on an event; subscribers run later,
    in their own task, and may live in another layer.
    """

    name: ClassVar[str] = "event"

    # Left out of equality: two events with the same data are the same event.
    occurred_at: datetime = dataclasses.field(
        default_factory=lambda: datetime.now(timezone.utc), compare=False)
