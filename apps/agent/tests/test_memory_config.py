from dataclasses import replace

import pytest

from az_maf_agent.api import configured_memory
from az_maf_agent.core import Principal
from az_maf_agent.memory import OPERATIONS, FixtureMemoryStore

TENANT = "c57afb80-6b3d-4bae-a466-e4d217bcb4a2"
USER = "6e79f1d2-3af5-4b89-a2fa-66a915419a25"
OTHER = "00000000-0000-4000-8000-000000000001"


def environment():
    return {
        "ENABLE_MEMORY": "true",
        "MEMORY_BACKEND": "azure_blob",
        "MEMORY_ACCOUNT": "fixtureaccount",
        "MEMORY_CONTAINER": "preferences",
        "MEMORY_POLICY": "config/memory-policy.json",
        "MEMORY_ALLOWED_USERS": USER,
        "ENTRA_TENANT_ID": TENANT,
        "ENTRA_ALLOWED_USERS": USER,
    }


def test_disabled_default_allocates_nothing():
    def unexpected(*args):
        raise AssertionError("disabled memory must not allocate a backend")

    assert configured_memory({}, store_factory=unexpected) == (None, None)


def test_hosted_memory_requires_authenticated_allowlisted_scope():
    destinations = []

    def factory(account, container):
        destinations.append((account, container))
        return FixtureMemoryStore()

    service, permissions = configured_memory(
        environment(), store_factory=factory, audit=lambda _: None
    )
    who = Principal(TENANT, USER, "entra")
    assert destinations == [("fixtureaccount", "preferences")]
    assert permissions(who) == OPERATIONS
    assert not permissions(replace(who, tenant=OTHER))
    assert not permissions(replace(who, user=OTHER))
    assert not permissions(replace(who, source="local"))
    assert service.policy.retention_seconds == 2592000


@pytest.mark.parametrize(
    "key,value",
    [
        ("ENABLE_MEMORY", "yes"),
        ("MEMORY_BACKEND", "arbitrary_connection_string"),
        ("MEMORY_ALLOWED_USERS", OTHER),
        ("MEMORY_ALLOWED_USERS", ""),
        ("ENTRA_TENANT_ID", "forged"),
    ],
)
def test_invalid_hosted_configuration_fails_before_backend_allocation(key, value):
    env = environment()
    env[key] = value

    def unexpected(*args):
        raise AssertionError("invalid configuration must fail before allocating a backend")

    with pytest.raises(ValueError):
        configured_memory(env, store_factory=unexpected)
