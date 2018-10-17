# -*- coding: utf-8 -*-

# pylint: disable=invalid-name, protected-access, unused-argument

import functools
import itertools

from django.db.migrations import autodetector
from django.db import models
from django.db.models.options import Options

from .kentta import Lumekentta


def puukota(moduuli, koriste=None, kopioi=None):
  '''
  Korvaa moduulissa olevan metodin tai lisää uuden (`kopioi`).
  '''
  def puukko(funktio):
    toteutus = getattr(moduuli, kopioi or funktio.__name__, None)
    def uusi_toteutus(*args, **kwargs):
      return funktio(toteutus, *args, **kwargs)
    setattr(
      moduuli, funktio.__name__,
      (koriste or functools.wraps(toteutus))(uusi_toteutus)
    )
  return puukko
  # def puukota


@puukota(autodetector.MigrationAutodetector)
def __init__(oletus, self, *args, **kwargs):
  '''
  Poista lumekentät migraatioiden luonnin yhteydessä
  sekä vanhojen että uusien kenttien listalta.
  '''
  oletus(self, *args, **kwargs)
  for malli in self.from_state.models.values():
    malli.fields = {
      l: f for l, f in malli.fields.items() if not isinstance(f, Lumekentta)
    }
  for malli in self.to_state.models.values():
    malli.fields = {
      l: f for l, f in malli.fields.items() if not isinstance(f, Lumekentta)
    }
  # def __init__


@puukota(Options, koriste=property)
def concrete_fields(oletus, self):
  '''
  Järjestä lumekentät viimeisiksi.

  Tätä tarvitaan uutta riviä luotaessa, jotta todellisten
  sarakkeiden arvot ovat käytettävissä lumekenttiä asetettaessa.
  '''
  return models.options.make_immutable_fields_list(
    "concrete_fields", itertools.chain((
      f for f in self.fields
      if f.concrete and not isinstance(f, Lumekentta)
    ), (
      f for f in self.fields
      if f.concrete and isinstance(f, Lumekentta)
    ))
  )
  # def concrete_fields


@puukota(Options, koriste=property)
def local_concrete_fields(oletus, self):
  '''
  Ohita lumekentät mallin konkreettisia kenttiä kysyttäessä.
  '''
  return models.options.make_immutable_fields_list(
    "local_concrete_fields", (
      f for f in self.local_fields
      if f.concrete and not isinstance(f, Lumekentta)
    )
  )
  # def local_concrete_fields


@puukota(models.query.QuerySet)
def _insert(oletus, self, objs, fields, **kwargs):
  '''
  Poista mahdolliset lumekentät tallennettavista kentistä.
  '''
  return oletus(self, objs, fields=[
    f for f in fields if not isinstance(f, Lumekentta)
  ], **kwargs)
  # def _insert


@puukota(models.query.QuerySet, kopioi='only')
def lume(only, self, *fields):
  '''
  Lisää annetut lumekentät pyydettyjen kenttien listalle, tai tyhjennä lista.
  '''
  if self._fields is not None:
    raise TypeError(
      'Ei voida kutsua metodia .lume()'
      ' aiemman .values()- tai .values_list()-kutsun jälkeen.'
    )
  clone = self._chain()
  if fields == (None,):
    clone.query.tyhjenna_lumekentat()
  else:
    clone.query.lisaa_lumekentat(fields)
  return clone
  # def lume


# Metodia `models.Manager._get_queryset_methods()` on tässä vaiheessa
# jo kutsuttu, joten kopioidaan `lume`-metodi käsin `Manager`-luokkaan:
def m_lume(self, *args, **kwargs):
  return getattr(self.get_queryset(), 'lume')(*args, **kwargs)
models.Manager.lume = m_lume


@puukota(models.sql.query.Query, kopioi='clear_deferred_loading')
def tyhjenna_lumekentat(oletus, self):
  self.pyydetyt_lumekentat = frozenset()
  # def tyhjenna_lumekentat


@puukota(models.sql.query.Query, kopioi='add_deferred_loading')
def lisaa_lumekentat(oletus, self, kentat):
  self.pyydetyt_lumekentat = getattr(
    self, 'pyydetyt_lumekentat', frozenset()
  ).union(kentat)
  # def lisaa_lumekentat


@puukota(models.sql.query.Query)
def deferred_to_data(oletus, self, target, callback):
  '''
  Lisää pyydetyt tai oletusarvoiset lumekentät kyselyyn
  ennen lopullisten kenttien määräämistä:
    1. `qs.only(...)` -> oletustoteutus (nimetyt kentät haetaan)
    2. `qs.defer(...).lume(...)` -> lisää ne ei-automaattiset lumekentät,
      joita ei nimetty, `defer`-luetteloon
    3. `qs.defer(...)` -> lisää ei-automaattiset lumekentät `defer`-luetteloon
    4. `qs.lume(...)` -> muodosta `defer`-luettelo ei-automaattisista,
      ei-nimetyistä lumekentistä
    5. `qs` -> muodosta `defer`-luettelo ei-automaattisista lumekentistä
  '''
  field_names, defer = self.deferred_loading
  if not defer: # `qs.only()`
    return oletus(self, target, callback)

  pyydetyt_lumekentat = getattr(self, 'pyydetyt_lumekentat', [])
  for kentta in self.get_meta().get_fields():
    if isinstance(kentta, Lumekentta) \
    and not kentta.automaattinen \
    and not kentta.name in pyydetyt_lumekentat \
    and (
      not isinstance(self.select_related, dict)
      or kentta.name not in self.select_related
    ):
      field_names = field_names.union((kentta.name,))

  self.deferred_loading = field_names, True
  return oletus(self, target, callback)
  # def deferred_to_data


@puukota(models.Model)
def get_deferred_fields(oletus, self):
  '''
  Älä sisällytä lumekenttiä malli-olion `get_deferred_fields()`-paluuarvoon.
  Tätä joukkoa kysytään mallin tallentamisen ja kannasta lataamisen yhteydessä.
  '''
  return {
    kentta for kentta in oletus(self)
    if not isinstance(self._meta.get_field(kentta), Lumekentta)
  }
  # def get_deferred_fields


@puukota(models.Model)
def refresh_from_db(oletus, self, **kwargs):
  '''
  Tyhjennä mahdolliset lumekentille aiemmin lasketut arvot;
  suorita sitten tavanomainen kantakysely.
  '''
  data = self.__dict__
  for kentta in self._meta.concrete_fields:
    if isinstance(kentta, Lumekentta):
      data.pop(kentta.name, None)
      data.pop(kentta.attname, None)
  return oletus(self, **kwargs)
  # def refresh_from_db
