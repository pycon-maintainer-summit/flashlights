from django.apps import AppConfig


class MaintainerSummitConfig(AppConfig):
    """The PyCon US Maintainer Summit's own app, loaded ahead of the core through
    ``EXTRA_APPS``: its static files (the logo and the share image) today,
    its own pages, models and commands when the Maintainer Summit needs them."""

    name = "flashlights_summit"
    verbose_name = "Maintainer Summit"
