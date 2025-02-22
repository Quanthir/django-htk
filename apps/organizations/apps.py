# Django Imports
from django.apps import AppConfig
from django.db.models import signals

# HTK Imports
from htk.app_config import HtkAppConfig


class HtkOrganizationAppConfig(HtkAppConfig):
    name = 'htk.apps.organizations'
    label = 'organizations'
    verbose_name = 'Organizations'

    def ready(self):
        pass
