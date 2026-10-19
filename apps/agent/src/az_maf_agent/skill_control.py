"""Read-only Azure Resource Manager tag control for the single-replica dev lesson."""

import logging
import re

import httpx
from azure.identity import ManagedIdentityCredential

from .model import Denied
from .skills import parse_control

CONTROL_TAG = "maf-skill-control"


class AzureTagControl:
    """The workload has Reader on its control resource; only operators can update resource tags.

    No cache: every gate reads ARM. Errors/timeout fail closed. The bounded tag store
    is for the two-skill teaching exercise, not a production shared control plane.
    """

    def __init__(self, resource_id, credential=None, http=None):
        if not re.fullmatch(
            r"/subscriptions/[0-9a-f-]{36}/resourceGroups/[A-Za-z0-9_.()-]{1,90}"
            r"(?:/providers/Microsoft.App/containerApps/[a-z0-9-]{1,32})?",
            resource_id,
        ):
            raise ValueError("invalid skill control resource")
        self.url = (
            "https://management.azure.com"
            + resource_id
            + "/providers/Microsoft.Resources/tags/default?api-version=2021-04-01"
        )
        self.credential = credential or ManagedIdentityCredential(
            connection_timeout=1, read_timeout=1, retry_total=0
        )
        self.http = http or httpx.Client(timeout=3.0, follow_redirects=False)

    def __call__(self):
        try:
            token = self.credential.get_token("https://management.azure.com/.default")
            for attempt in range(2):
                try:
                    with self.http.stream(
                        "GET", self.url, headers={"Authorization": "Bearer " + token.token}
                    ) as response:
                        if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                            continue
                        if response.status_code != 200:
                            raise ValueError("control response")
                        data = bytearray()
                        for chunk in response.iter_bytes():
                            data.extend(chunk)
                            if len(data) > 16384:
                                raise ValueError("control response too large")
                    break
                except (httpx.TimeoutException, httpx.NetworkError):
                    if attempt:
                        raise
            import json

            state = json.loads(data)["properties"]["tags"][CONTROL_TAG]
            if not isinstance(state, str) or len(state) > 256:
                raise ValueError("invalid control tag")
            return parse_control(state)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "skill_control_read_failed category=%s", type(exc).__name__
            )
            raise Denied("skill_control_unavailable") from None

    def close(self):
        self.http.close()
        self.credential.close()
