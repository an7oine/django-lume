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
# @created     17.10.2018
# @author      Antti Hautaniemi <antti.hautaniemi@pispalanit.fi>
# @copyright   Copyright (c) Pispalan Insinööritoimisto Oy
# @license     All rights reserved
#============================================================================
# pylint: disable=invalid-name

from functools import wraps
import inspect

from django.db import models

from lume.kentta import Lumekentta


# Lisää `models.Manager.get_queryset`-metodin palauttamaan kyselyjoukkoon
# ne mallissa määritetyt `Lumekentät`, jotka on asetettu `automaattisiksi`
vanha_get_queryset = models.Manager.get_queryset

@wraps(vanha_get_queryset)
def get_queryset(self):
  qs = vanha_get_queryset(self)

  for nimi, lumekentta in inspect.getmembers(
    qs.model, lambda k: isinstance(k, Lumekentta) and k.automaattinen
  ):
    qs = qs.annotate(**{
      #nimi + '_id' if isinstance(
      #  lumekentta.kysely.output_field, models.ForeignKey
      #) else nimi: lumekentta.kysely
      nimi: lumekentta.kysely
    })
    # for nimi, lumekentta

  return qs
  # def get_queryset

models.Manager.get_queryset = get_queryset


# Lisää kyselyjoukkoon metodi `lume`, joka lisää nimetyt lumekentät kyselyyn
@wraps(models.QuerySet.only)
def lume(self, *fields):
  return self.annotate(**{
    nimi: getattr(self.model, nimi).kysely
    for nimi in fields
    if isinstance(getattr(self.model, nimi, None), Lumekentta)
    and not getattr(self.model, nimi).automaattinen
  })
  # def lume
models.QuerySet.lume = lume


vanha_iter = models.query.ModelIterable.__iter__
@wraps(vanha_iter)
def __iter__(self):
  laske = []
  poista = []
  for nimi, lumekentta in inspect.getmembers(
    self.queryset.model, lambda k: isinstance(k, Lumekentta)
  ):
    if lumekentta.laske:
      laske += [(nimi, lumekentta.laske)]
    else:
      poista += [nimi]
    # nimi, lumekentta
  for rivi in vanha_iter(self):
    for nimi, laske_funktio in laske:
      if isinstance(getattr(rivi, nimi), Lumekentta):
        setattr(rivi, nimi, laske_funktio(rivi))
    for nimi in poista:
      if isinstance(getattr(rivi, nimi), Lumekentta):
        delattr(rivi, nimi)
    yield rivi
    # for rivi
  # def __iter__
models.query.ModelIterable.__iter__ = __iter__
