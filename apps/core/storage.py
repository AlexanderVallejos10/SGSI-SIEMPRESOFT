import os

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class StaticConVersion(StaticFilesStorage):
    def url(self, name):
        url = super().url(name)
        if not name:
            return url
        ruta = finders.find(name)
        if not ruta and self.location and os.path.exists(os.path.join(self.location, name)):
            ruta = os.path.join(self.location, name)
        if not ruta or isinstance(ruta, list):
            return url
        return f"{url}?v={int(os.path.getmtime(ruta))}"
