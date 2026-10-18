"""Stage 1 public-client authentication with an encrypted local token cache."""

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from azure.identity import (
    AuthenticationRecord,
    AuthenticationRequiredError,
    DeviceCodeCredential,
    TokenCachePersistenceOptions,
)

TENANT_ID = "c57afb80-6b3d-4bae-a466-e4d217bcb4a2"
API_APP_ID = "e7898571-069f-49c7-91b5-4b08a9edcb30"
CLI_APP_ID = "df915b12-fb46-48d7-a80f-6f2e8e9ef487"
SCOPE = f"api://{API_APP_ID}/Chat.Access"

# The platform encrypts this cache for the current OS user. Do not permit plaintext fallback.
CACHE_OPTIONS = TokenCachePersistenceOptions(name="az-maf-agent-stage1")
AUTH_RECORD_PATH = Path.home() / ".config" / "az-maf-agent-stage1" / "authentication-record.json"
DeviceCodePrompt = Callable[[str, str, datetime], None]


def _load_authentication_record() -> AuthenticationRecord | None:
    try:
        return AuthenticationRecord.deserialize(AUTH_RECORD_PATH.read_text())
    except (OSError, ValueError):
        return None


def _save_authentication_record(record: AuthenticationRecord) -> None:
    AUTH_RECORD_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = AUTH_RECORD_PATH.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write(record.serialize())
    os.replace(temporary, AUTH_RECORD_PATH)


def _credential(prompt_callback: DeviceCodePrompt, record: AuthenticationRecord | None):
    return DeviceCodeCredential(
        tenant_id=TENANT_ID,
        client_id=CLI_APP_ID,
        prompt_callback=prompt_callback,
        cache_persistence_options=CACHE_OPTIONS,
        authentication_record=record,
        disable_automatic_authentication=record is not None,
    )


def acquire_stage1_token(prompt_callback: DeviceCodePrompt) -> str:
    """Return a short-lived API token, silently refreshing when local state permits."""
    record = _load_authentication_record()
    credential = _credential(prompt_callback, record)
    try:
        if record is not None:
            try:
                return credential.get_token(SCOPE).token
            except AuthenticationRequiredError:
                pass
        record = credential.authenticate(scopes=[SCOPE])
        _save_authentication_record(record)
        return credential.get_token(SCOPE).token
    finally:
        credential.close()
