"""Write the web API's OpenAPI schema (/api/v1/openapi.json) to a file.

    poetry run python scripts/export_openapi.py web/openapi.json

``web/``'s ``npm run gen:api`` runs this and then generates ``src/api/schema.d.ts``
from the file. Without a ``config.py`` it loads ``config.example.py``, like the tests; it needs
no database or network.
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import _install_example_config, _stub_google_clients  # noqa: E402


async def export() -> dict:
    from alttprbot_api.api import sahasrahbotapi

    client = sahasrahbotapi.test_client()
    response = await client.get('/api/v1/openapi.json')
    return await response.get_json()


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    _install_example_config()
    _stub_google_clients()
    schema = asyncio.run(export())
    Path(sys.argv[1]).write_text(json.dumps(schema, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
