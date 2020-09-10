#!/usr/bin/python
# vi: et sw=2 fileencoding=utf-8

#============================================================================
# Lume
# Copyright (c) 2020 Pispalan Insinööritoimisto Oy (http://www.pispalanit.fi)
#
# All rights reserved.
# Redistributions of files must retain the above copyright notice.
#
# @description [File description]
# @created     10.09.2020
# @author      Antti Hautaniemi <antti.hautaniemi@pispalanit.fi>
# @copyright   Copyright (c) Pispalan Insinööritoimisto Oy
# @license     All rights reserved
#============================================================================

from django.db import models


class Lumemaare(models.query_utils.DeferredAttribute):

  def __get__(self, instance, cls=None):
    '''
    Kysyttäessä kenttää, jota ei luettu kannasta,
    haetaan sen arvo `laske_paikallisesti`-metodin avulla.

    Vrt. super.
    '''
    if instance is None:
      return self
    data = instance.__dict__
    field_name = self.field.attname
    if data.get(field_name, self) is self:
      val = self._check_parent_chain(instance)
      if val is None:
        # Lasketaan arvo paikallisesti tai kysytään kannasta.
        val = self.field.laske_paikallisesti(instance)
      data[field_name] = val
    return data[field_name]
    # def __get__

  def __set__(self, instance, value):
    '''
    Jos kentän arvo asetetaan suoraan kutsuvasta koodista,
    kutsutaan `aseta_paikallisesti`-metodia.
    '''
    if instance is None:
      return
    data = instance.__dict__
    field_name = self.field.attname
    aiempi_arvo = data.get(field_name, self)
    if aiempi_arvo is self:
      aiempi_arvo = self._check_parent_chain(instance) or self

    if aiempi_arvo is not self and aiempi_arvo != value:
      # Jos arvo on jo olemassa eikä se muutu, ei tehdä mitään.
      # Muuten mm. `django.db.models.query.ModelIterable.__iter__` kaatuu.
      self.field.aseta_paikallisesti(instance, value)

    data[field_name] = value
    # def __set__

  # class Lumemaare