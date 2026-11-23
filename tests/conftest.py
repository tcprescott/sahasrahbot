"""Shared pytest setup.

SahasrahBot reads settings from a gitignored ``config.py`` at import time. When
that file is absent (CI, a fresh clone, a cloud agent session), load
``config.example.py`` in its place so modules can be imported with harmless
placeholder values. A real local ``config.py`` is used as-is.

``alttprbot/util/gsheet.py`` builds a Google Drive client at import time from a
service-account key. The placeholder key is empty, so that client is stubbed out
for the test run; no test talks to Google.
"""

import importlib.util
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_example_config() -> None:
    if (ROOT / "config.py").exists() or "config" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location("config", ROOT / "config.example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["config"] = module


def _stub_google_clients() -> None:
    try:
        import googleapiclient.discovery
        import oauth2client.service_account
    except ImportError:
        return
    mock.patch.object(
        oauth2client.service_account.ServiceAccountCredentials,
        "from_json_keyfile_dict",
        return_value=None,
    ).start()
    mock.patch.object(googleapiclient.discovery, "build", return_value=mock.MagicMock()).start()


_install_example_config()
_stub_google_clients()
