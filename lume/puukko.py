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
def get_select_mask(oletus, self):
  field_names, defer = self.deferred_loading
  if not field_names and defer:
    return self._get_defer_select_mask(self.get_meta(), {})
  return oletus(self)
  # def get_select_mask

@puukota(models.sql.query.Query)
def _get_defer_select_mask(oletus, self, opts, mask, select_mask=None):
  if self.model is not opts.model:
    return oletus(self, opts, mask, select_mask=select_mask)

  if select_mask is None:
    select_mask = {}

  for pyydetty_lumekentta in getattr(self, 'pyydetyt_lumekentat', ()):
    _opts, _select_mask = opts, select_mask
    for fn in pyydetty_lumekentta.split(models.sql.query.LOOKUP_SEP):
      kentta = _opts.get_field(fn)
      _select_mask = _select_mask.setdefault(kentta, {})
      try:
        _opts = kentta.remote_field.model._meta.concrete_model._meta
      except AttributeError:
        break

  def taydenna_maski(opts, mask, select_related):
    for kentta in opts.get_fields():
      if kentta.is_relation \
      and isinstance(self.select_related, dict) \
      and (_select_related := select_related.get(kentta.name)) is not None:
        if kentta.name not in mask and not taydenna_maski(
          kentta.remote_field.model._meta.concrete_model._meta,
          mask.setdefault(kentta.name, {}),
          _select_related,
        ):
          mask.pop(kentta.name)
      elif isinstance(kentta, Lumekentta) and not kentta.automaattinen:
        mask.setdefault(kentta.name, {})
    return mask
    # def taydenna_maski
  taydenna_maski(opts, mask, self.select_related)

  return oletus(self, opts, mask, select_mask=select_mask)
  # def _get_defer_select_mask


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
