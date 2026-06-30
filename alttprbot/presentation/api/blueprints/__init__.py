from .asynctournament import asynctournament_blueprint
from .presets import presets_blueprint
from .racetime import racetime_blueprint
from .settingsgen import settingsgen_blueprint
from .tournament import tournament_blueprint

REST_BLUEPRINTS = (
    (asynctournament_blueprint, {"url_prefix": "/async"}),
    (presets_blueprint, {}),
    (racetime_blueprint, {}),
    (settingsgen_blueprint, {}),
    (tournament_blueprint, {}),
)
