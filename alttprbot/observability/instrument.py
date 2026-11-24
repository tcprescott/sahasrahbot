"""Time every call into the service layer, the API clients and the seed generators.

:func:`instrument_all` runs once from ``init_sentry``. It wraps each public
``async`` function and method defined in these packages:

=================================  ================  ==========================
Package                            Metric prefix     Span op
=================================  ================  ==========================
``alttprbot/services/``            ``service``       ``service``
``alttprbot/integrations/``        ``integration``   ``integration``
``alttprbot/alttprgen/randomizer`` ``randomizer``    ``randomizer``
``alttprbot/alttprgen/generator``  ``seed``          ``seed.generate``
=================================  ================  ==========================

Each call emits ``<prefix>.calls`` (counter) and ``<prefix>.duration``
(distribution, ms), with ``target`` (``presets.get_preset``,
``ALTTPRClient.generate``) and ``outcome`` (``ok``, ``rejected``, ``cancelled``,
``error``). Inside a traced request, job or command it is also a child span, so
a slow trace shows which service or randomizer it waited on. Outside one it opens
no span: a call is never a trace of its own.

The wrapping is in place on the module and class objects, so callers that look
the function up at call time (``presets.get_preset(...)``, ``ALTTPRClient(...)``)
see it. A function imported by name before ``init_sentry`` ran
(``from x import f``) keeps the unwrapped one; that only costs its metrics.
Nothing here changes what a call returns or raises.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import logging
import pkgutil
import time
from types import ModuleType
from typing import Any, Callable, Iterable

import sentry_sdk

from alttprbot.observability import metrics

logger = logging.getLogger(__name__)

_MARK = '__sahasrahbot_instrumented__'

# (package or module, metric prefix, span op)
TARGETS = (
    ('alttprbot.services', 'service', 'service'),
    ('alttprbot.integrations', 'integration', 'integration'),
    ('alttprbot.alttprgen.randomizer', 'randomizer', 'randomizer'),
    ('alttprbot.alttprgen.generator', 'seed', 'seed.generate'),
)

# Plumbing, not domain work: the scheduler times its own jobs, and bots.py is sync.
SKIPPED_MODULES = {
    'alttprbot.services.scheduler',
    'alttprbot.services.scheduled_jobs',
    'alttprbot.services.bots',
}


def _owner_name(first: Any) -> str:
    return first.__name__ if isinstance(first, type) else type(first).__name__


def wrap(func: Callable[..., Any], prefix: str, op: str, target: str,
         method: str | None = None) -> Callable[..., Any]:
    """An async function that behaves like ``func`` and records each call.

    For a method pass its name as ``method``: the target is then named after the
    class it was called on (``SMZ3Preset.generate``, not the ``SMPreset`` that
    defines it), so subclasses that share a method stay apart.
    """
    if getattr(func, _MARK, False):
        return func

    @functools.wraps(func)
    async def instrumented(*args: Any, **kwargs: Any) -> Any:
        name = f'{_owner_name(args[0])}.{method}' if method and args else target
        attributes = {'target': name}
        started = time.perf_counter()
        try:
            if sentry_sdk.get_current_span() is None:
                result = await func(*args, **kwargs)
            else:
                with sentry_sdk.start_span(name=name, attributes={'sentry.op': op}):
                    result = await func(*args, **kwargs)
        except BaseException as e:
            metrics.record_call(prefix, started, e, attributes)
            raise
        metrics.record_call(prefix, started, None, attributes)
        return result

    setattr(instrumented, _MARK, True)
    return instrumented


def _is_public_coroutine(name: str, obj: Any) -> bool:
    return not name.startswith('_') and inspect.iscoroutinefunction(obj)


def instrument_class(cls: type, prefix: str, op: str) -> int:
    """Wrap ``cls``'s own public async methods (plain, class and static). Returns how many."""
    wrapped = 0
    for name, attr in list(vars(cls).items()):
        if name.startswith('_'):
            continue
        target = f'{cls.__name__}.{name}'
        if isinstance(attr, classmethod) and inspect.iscoroutinefunction(attr.__func__):
            setattr(cls, name, classmethod(wrap(attr.__func__, prefix, op, target, method=name)))
        elif isinstance(attr, staticmethod) and inspect.iscoroutinefunction(attr.__func__):
            setattr(cls, name, staticmethod(wrap(attr.__func__, prefix, op, target)))
        elif _is_public_coroutine(name, attr):
            setattr(cls, name, wrap(attr, prefix, op, target, method=name))
        else:
            continue
        wrapped += 1
    return wrapped


def instrument_module(module: ModuleType, prefix: str, op: str) -> int:
    """Wrap the public async functions and classes defined in ``module``. Returns how many."""
    short = module.__name__.rsplit('.', 1)[-1]
    wrapped = 0
    for name, obj in list(vars(module).items()):
        if getattr(obj, '__module__', None) != module.__name__ or name.startswith('_'):
            continue
        if inspect.isclass(obj):
            wrapped += instrument_class(obj, prefix, op)
        elif _is_public_coroutine(name, obj):
            setattr(module, name, wrap(obj, prefix, op, f'{short}.{name}'))
            wrapped += 1
    return wrapped


def _module_names(dotted: str) -> Iterable[str]:
    yield dotted
    module = importlib.import_module(dotted)
    if hasattr(module, '__path__'):
        for info in pkgutil.iter_modules(module.__path__, prefix=f'{dotted}.'):
            if info.name not in SKIPPED_MODULES:
                yield info.name


def instrument_all() -> int:
    """Instrument every module in :data:`TARGETS`. A module that fails is logged and skipped."""
    total = 0
    for dotted, prefix, op in TARGETS:
        try:
            names = list(_module_names(dotted))
        except Exception:
            logger.exception('Could not instrument %s for Sentry', dotted)
            continue
        for name in names:
            try:
                total += instrument_module(importlib.import_module(name), prefix, op)
            except Exception:
                logger.exception('Could not instrument %s for Sentry', name)
    return total
