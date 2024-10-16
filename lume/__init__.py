# -*- coding: utf-8 -*-

import inspect

from django.db import models

from .kentta import EI_ASETETTU, Lumekentta
from . import puukko


# Nimetään eri kenttäluokat tässä, jotta koodintarkistusalgoritmit eivät
# valita niistä.
# Luettelo per Django 5.1.
AutoField: type
BigAutoField: type
BigIntegerField: type
BinaryField: type
BooleanField: type
CharField: type
CommaSeparatedIntegerField: type
DateField: type
DateTimeField: type
DecimalField: type
DurationField: type
EmailField: type
Field: type
FilePathField: type
FloatField: type
GeneratedField: type
GenericIPAddressField: type
IPAddressField: type
IntegerField: type
NullBooleanField: type
PositiveBigIntegerField: type
PositiveIntegerField: type
PositiveSmallIntegerField: type
SlugField: type
SmallAutoField: type
SmallIntegerField: type
TextField: type
TimeField: type
URLField: type
UUIDField: type
FileField: type
ImageField: type
JSONField: type
ForeignKey: type
OneToOneField: type


# Periytä lumeversio kustakin Djangon kenttätyypistä.
for nimi, luokka in inspect.getmembers(
  models, lambda x: inspect.isclass(x) and issubclass(x, models.Field)
):
  globals()[nimi] = type(nimi, (Lumekentta, luokka), {})
del inspect
del models
