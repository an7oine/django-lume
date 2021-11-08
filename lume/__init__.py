# -*- coding: utf-8 -*-

import inspect

from django.db import models

from .kentta import EI_ASETETTU, Lumekentta
from . import puukko

# Periytä lumeversio kustakin Djangon kenttätyypistä.
for nimi, luokka in inspect.getmembers(
  models, lambda x: inspect.isclass(x) and issubclass(x, models.Field)
):
  globals()[nimi] = type(nimi, (Lumekentta, luokka), {})
del inspect
del models
