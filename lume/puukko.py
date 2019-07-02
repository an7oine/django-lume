#!/usr/bin/python
# vi: et sw=2 fileencoding=utf-8

#============================================================================
# Lume
# Copyright (c) 2018 Pispalan Insinööritoimisto Oy (http://www.pispalanit.fi)
#
# All rights reserved.
# Redistributions of files must retain the above copyright notice.
#
# @description [File description]
# @created     26.10.2018
# @author      Antti Hautaniemi <antti.hautaniemi@pispalanit.fi>
# @copyright   Copyright (c) Pispalan Insinööritoimisto Oy
# @license     All rights reserved
#============================================================================
# pylint: disable=invalid-name, protected-access, unused-argument

from __future__ import unicode_literals

import functools

from django.db.migrations import autodetector
from django.db import models
from django.db.models.options import Options

# pylint: disable=import-error
from .kentta import Lumesaate
# pylint: enable=import-error


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
    malli.fields = [f for f in malli.fields if not isinstance(f[1], Lumesaate)]
  for malli in self.to_state.models.values():
    malli.fields = [f for f in malli.fields if not isinstance(f[1], Lumesaate)]
  # def __init__


@puukota(Options, koriste=property)
def local_concrete_fields(oletus, self):
  '''
  Ohita lumekentät mallin konkreettisia kenttiä kysyttäessä.
  '''
  return models.options.make_immutable_fields_list(
    "concrete_fields", (
      f for f in self.local_fields
      if f.concrete and not isinstance(f, Lumesaate)
    )
  )
  # def local_concrete_fields


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
    if isinstance(kentta, Lumesaate) \
    and not kentta.automaattinen \
    and not kentta.name in pyydetyt_lumekentat:
      field_names = field_names.union((kentta.name,))

  self.deferred_loading = field_names, True
  return oletus(self, target, callback)
  # def deferred_to_data


@puukota(models.expressions.Col)
def as_sql(oletus, self, compiler, connection):
  '''
  Pyydä lumekenttää vastaavan sarakkeen SQL-kysely kentältä itseltään.
  '''
  # pylint: disable=redefined-outer-name
  if isinstance(self.target, Lumesaate):
    return self.target.sql_select(compiler)
  else:
    return oletus(self, compiler, connection)
  # def as_sql


@puukota(models.Model)
def get_deferred_fields(oletus, self):
  '''
  Älä sisällytä lumekenttiä malli-olion `get_deferred_fields()`-paluuarvoon.
  Tätä joukkoa kysytään mallin tallentamisen ja kannasta lataamisen yhteydessä.
  '''
  return {
    kentta for kentta in oletus(self)
    if not isinstance(self._meta.get_field(kentta), Lumesaate)
  }
  # def get_deferred_fields
