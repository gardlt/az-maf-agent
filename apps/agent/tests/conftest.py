import pytest

from az_maf_agent.config import Settings, load_settings


@pytest.fixture
def settings():
    return load_settings("config/offline.json")


@pytest.fixture
def configured(settings):
    def make(**changes):
        data = settings.model_dump()
        limits = changes.pop("limits", {})
        data["limits"].update(limits)
        data.update(changes)
        return Settings.model_validate(data)

    return make
