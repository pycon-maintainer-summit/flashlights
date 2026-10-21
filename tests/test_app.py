"""The app on the pinned core: loaded ahead of the core, its static files
collected, and the Maintainer Summit preset loading into a fresh database. Run
inside the image (``make test``), where the core's settings and pytest
configuration apply."""

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import override_settings

from portal.models import Conference

PRESET = Path("/community/presets/summit")


def test_the_app_is_loaded_ahead_of_the_core():
    apps = list(settings.INSTALLED_APPS)
    assert apps.index("flashlights_summit") < apps.index("portal")


@pytest.mark.parametrize("name", ["logo.svg", "favicon.svg"])
def test_the_images_the_identity_variables_point_at_exist(name):
    assert finders.find(f"flashlights_summit/{name}")


@pytest.mark.django_db
def test_the_preset_loads():
    with override_settings(DEBUG=True):
        call_command("load_preset", str(PRESET))
    assert Conference.objects.exists()
