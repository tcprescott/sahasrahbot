"""Write the web API's OpenAPI schema (/api/v1/openapi.json) to a file.

    poetry run python scripts/export_openapi.py web/openapi.json

``web/``'s ``npm run gen:api`` runs this and then generates ``src/api/schema.d.ts``
from the file. Without a ``config.py`` it loads ``config.example.py``, like the tests; it needs
no database or network.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# The same set-up as tests/conftest.py, copied so this script needs no pytest
# (CI's web job and a production build install only the app's dependencies).
def _install_example_config() -> None:
    if (ROOT / 'config.py').exists() or 'config' in sys.modules:
        return
    spec = importlib.util.spec_from_file_location('config', ROOT / 'config.example.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['config'] = module


def _stub_google_clients() -> None:
    try:
        import googleapiclient.discovery
        import oauth2client.service_account
    except ImportError:
        return
    mock.patch.object(
        oauth2client.service_account.ServiceAccountCredentials, 'from_json_keyfile_dict', return_value=None
    ).start()
    mock.patch.object(googleapiclient.discovery, 'build', return_value=mock.MagicMock()).start()


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
    out = Path(sys.argv[1]).resolve()
    if not out.is_relative_to(ROOT):
        sys.exit(f'{out} is outside the repository')
    out.write_text(json.dumps(schema, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
