"""Stage 1 public-client authentication with an encrypted local token cache."""

from collections.abc import Callable
from datetime import datetime

from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions

TENANT_ID = "c57afb80-6b3d-4bae-a466-e4d217bcb4a2"
API_APP_ID = "e7898571-069f-49c7-91b5-4b08a9edcb30"
CLI_APP_ID = "df915b12-fb46-48d7-a80f-6f2e8e9ef487"
SCOPE = f"api://{API_APP_ID}/Chat.Access"

# The platform encrypts this cache for the current OS user. Do not permit plaintext fallback.
CACHE_OPTIONS = TokenCachePersistenceOptions(name="az-maf-agent-stage1")
DeviceCodePrompt = Callable[[str, str, datetime], None]


def acquire_stage1_token(prompt_callback: DeviceCodePrompt) -> str:
    """Return a short-lived API token, refreshing the encrypted cache when possible."""
    credential = DeviceCodeCredential(
        tenant_id=TENANT_ID,
        client_id=CLI_APP_ID,
        prompt_callback=prompt_callback,
        cache_persistence_options=CACHE_OPTIONS,
    )
    try:
        return credential.get_token(SCOPE).token
    finally:
        credential.close()
