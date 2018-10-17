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

import functools

from django.db import models
from django.db.migrations import autodetector
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
  if isinstance(self.target, Lumesaate):
    return self.target.select_format(compiler, None, None)
  else:
    return oletus(self, compiler, connection)
  # def as_sql


@puukota(models.options.Options, koriste=cached_property)
def local_concrete_fields(oletus, self):
  '''
  Ohita lumekentät mallin konkreettisia kenttiä kysyttäessä.
  '''
  return models.options.make_immutable_fields_list(
    "concrete_fields", (
      f for f in self.fields if f.concrete and not isinstance(f, Lumesaate)
    )
  )
  # def local_concrete_fields
