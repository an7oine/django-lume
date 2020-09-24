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

import functools

from django.db import models
from django.utils.functional import cached_property, classproperty

from .maare import Lumemaare
from .sarake import Lumesarake


EI_ASETETTU = object()


class Lumekentta(models.fields.Field):

  @classproperty
  def descriptor_class(cls):
    # pylint: disable=no-self-argument, invalid-name
    @functools.wraps(super().descriptor_class, updated=())
    class descriptor_class(Lumemaare, super().descriptor_class): pass
    return descriptor_class
    # def descriptor_class

  def __init__(
    self, *args,
    kysely, laske=None, aseta=None, automaattinen=False,
    **kwargs
  ):
    '''
    Alustaa lumekentän.
    Args:
      kysely (`django.db.models.Expression` / `lambda`): kysely
      laske (`lambda self`): paikallinen laskentafunktio
      aseta (`lambda *args`): paikallinen arvon asetusfunktio
      automaattinen (`bool`): lisätäänkö kenttä automaattisesti kyselyyn?
    '''
    # Lisää super-kutsuun parametri `editable=False`,
    # jos `aseta`-funktiota ei ole määritetty.
    if not aseta:
      kwargs['editable'] = False

    super().__init__(*args, **kwargs)

    self.default = EI_ASETETTU

    self._kysely = kysely
    self._laske = laske
    self._aseta = aseta
    self.automaattinen = automaattinen

    self.serialize = False
    # def __init__

  def deconstruct(self):
    name, path, args, kwargs = super().deconstruct()
    return name, path, args, dict(
      kysely=self.kysely,
      **kwargs
    )
    # def deconstruct

  @property
  def kysely(self):
    ''' Hae kyselylauseke (joko lambda tai suora arvo) '''
    return self._kysely() if callable(self._kysely) else self._kysely
    # def kysely
  @kysely.setter
  def kysely(self, kysely):
    self._kysely = kysely
    # def kysely

  def laske_paikallisesti(self, rivi):
    '''
    Lasketaan kentän arvo paikallisesti, jos laskentafunktio on määritelty;
    muuten kysytään kenttää erikseen kannasta.
    '''
    # pylint: disable=protected-access
    if callable(self._laske):
      return self._laske(rivi)
    else:
      # Vrt. `django.db.models.Model.refresh_from_db`.
      qs = rivi.__class__._base_manager.db_manager(
        None, hints={'instance': rivi}
      ).filter(pk=rivi.pk).only(self.attname)
      try:
        return getattr(qs.get(), self.attname)
      except qs.model.DoesNotExist:
        return None
    # def laske_paikallisesti

  def aseta_paikallisesti(self, rivi, arvo):
    '''
    Asetetaan kentän arvo paikallisesti, jos asetusfunktio on annettu;
    muuten nostetaan poikkeus.
    '''
    if not callable(self._aseta):
      raise RuntimeError('Asetusfunktiota ei ole määritetty: %s' % self)
    return self._aseta(rivi, arvo)
    # def aseta_paikallisesti

  def get_col(self, alias, output_field=None):
    # Ks. `Field.get_col`.
    if output_field is None:
      if isinstance(self, models.ForeignKey):
        # Ks. `ForeignKey.get_col`.
        # pylint: disable=no-member
        output_field = self.target_field
        while isinstance(output_field, models.ForeignKey):
          output_field = output_field.target_field
          if output_field is self:
            raise ValueError('Cannot resolve output_field.')
        # if isinstance
      else:
        output_field = self
    if alias != self.model._meta.db_table or output_field != self:
      return Lumesarake(alias, self, output_field)
    else:
      return self.cached_col
    # def get_col

  @cached_property
  def cached_col(self):
    return Lumesarake(self.model._meta.db_table, self)
    # def cached_col

  def get_joining_columns(self, reverse_join=False):
    ''' Ohita normaali JOIN-ehto (`a`.`id` = `b`.`a_id`) '''
    # pylint: disable=unused-argument
    return tuple()
    # def get_joining_columns

  def get_extra_restriction(self, where_class, alias, related_alias):
    '''
    Luo JOIN-ehto muotoa (`a`.`id` = (SELECT ... from `b`)).

    Tätä kutsutaan vain `ForeignObject`-tyyppiselle kentälle.
    '''
    # pylint: disable=unused-argument, no-member
    rhs_field = self.related_fields[0][1]
    field = rhs_field.model._meta.get_field(rhs_field.column)
    return field.get_lookup('exact')(
      self.get_col(related_alias),
      field.get_col(alias),
    )
    # def get_extra_restriction

  # class Lumekentta
