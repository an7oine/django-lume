import inspect

from django.db import models

from .kentta import Lumesaate
from . import puukko

for nimi, luokka in inspect.getmembers(
  models, lambda x: inspect.isclass(x) and issubclass(x, models.Field)
):
  globals()[nimi] = type(nimi, (Lumesaate, luokka), {})
