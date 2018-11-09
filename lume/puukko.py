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
from django.db.models.sql import compiler
from django.db.models.options import Options
from django.utils.functional import cached_property

# pylint: disable=import-error
from .kentta import Lumesaate
# pylint: enable=import-error


def puukota(moduuli, koriste=None, kopioi=None):
  '''
  Korvaa moduulissa olevan metodin tai lisää uuden (`kopioi`).
  '''
  koriste = koriste or (lambda f: f)
  def puukko(funktio):
    nimi = kopioi or funktio.__name__
    toteutus = getattr(moduuli, nimi, None)
    @functools.wraps(toteutus)
    @koriste
    def uusi_toteutus(*args, **kwargs):
      return funktio(toteutus, *args, **kwargs)
    setattr(moduuli, funktio.__name__, uusi_toteutus)
  return puukko
  # def puukota


@puukota(autodetector.MigrationAutodetector)
def _prepare_field_lists(oletus, self):
  '''
  Poista lumekentät migraatioiden luonnin yhteydessä
  sekä vanhojen että uusien kenttien listalta.
  '''
  oletus(self)
  self.old_field_keys = {
    (app_label, model_name, field_name)
    for app_label, model_name, field_name in self.old_field_keys
    if not isinstance(self.old_apps.get_model(
      app_label, model_name
    )._meta.get_field(field_name), Lumesaate)
  }
  self.new_field_keys = {
    (app_label, model_name, field_name)
    for app_label, model_name, field_name in self.new_field_keys
    if not isinstance(self.new_apps.get_model(
      app_label, model_name
    )._meta.get_field(field_name), Lumesaate)
  }
  # def _prepare_field_lists


#@puukota(Options, koriste=cached_property)
def local_concrete_fields(self):
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
Options.local_concrete_fields = cached_property(local_concrete_fields)


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
    clone.query.pyydetyt_lumekentat = []
  else:
    clone.query.pyydetyt_lumekentat = getattr(
      clone.query, 'pyydetyt_lumekentat', []
    ) + list(fields)
  return clone
  # def lume


# Metodia `models.Manager._get_queryset_methods()` on tässä vaiheessa
# jo kutsuttu, joten kopioidaan `lume`-metodi käsin `Manager`-luokkaan:
def m_lume(self, *args, **kwargs):
  return getattr(self.get_queryset(), 'lume')(*args, **kwargs)
models.Manager.lume = m_lume


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


@puukota(compiler.SQLCompiler)
def get_converters(oletus, self, expressions):
  '''
  Korjaa SQL-kääntäjän käyttämät kenttätyyppi- ja tietokantatoteutuskohtaiset
  muuntimet siten, että
  {DEFERRED}-arvot palautetaan sellaisenaan (ei yritetä muuntaa niitä).
  '''
  def korjaa_muunnin(muunnin):
    @functools.wraps(muunnin)
    def korjattu_muunnin(value, *args, **kwargs):
      if value == str(models.base.DEFERRED):
        return value
      else:
        return muunnin(value, *args, **kwargs)
    return korjattu_muunnin
  return {
    i: (list(map(korjaa_muunnin, convs)), expression)
    for i, (convs, expression) in oletus(self, expressions).items()
  }
  # def get_converters
