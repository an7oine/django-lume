# -*- coding: utf-8 -*-

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
        val = self.field.laske_paikallisesti(
          instance,
          select_related=False,
        )
      data[field_name] = val
    return data[field_name]
    # def __get__

  def __set__(self, instance, value):
    '''
    Jos kentän arvo asetetaan suoraan kutsuvasta koodista,
    kutsutaan `aseta_paikallisesti`-metodia.
    '''
    if instance is None or value is self.field.default:
      return
    data = instance.__dict__
    field_name = self.field.attname

    # Uusi rivi: asetetaan paikallisesti ja lisätään dataan.
    if not data.get(instance._meta.pk.attname):
      self.field.aseta_paikallisesti(instance, value)
      data[field_name] = value

    # Olemassaoleva rivi: verrataan mahdolliseen jo laskettuun
    # tai aiemmin noudettuun arvoon.
    else:
      aiempi_arvo = data.get(field_name, self)
      if aiempi_arvo is self:
        aiempi_arvo = self._check_parent_chain(instance) or self
      if aiempi_arvo is self:
        data[field_name] = value
      elif aiempi_arvo != value:
        self.field.aseta_paikallisesti(instance, value)
        data[field_name] = value
      # else:
      #   Jos arvo on jo olemassa eikä se muutu, ei tehdä mitään.
      #   Muuten mm. `django.db.models.query.ModelIterable.__iter__` kaatuu.
    # def __set__

  # class Lumemaare


class LumeFM2OMaare:
  def get_object(self, instance):
    '''
    Kysyttäessä viittausta toiseen malliin, jota ei ole välimuistissa,
    haetaan sen sisältö `laske_paikallisesti(select_related=True)`-kutsun
    avulla.

    Vrt. esim. ForwardManyToOneDescriptor.get_object.
    '''
    # pylint: disable=no-member
    # Huomaa, että `self.field` asetetaan kaikille kenttätyyppikohtaisille
    # Django-kuvaajille, joista käsillä oleva luokka voidaan periyttää.
    return self.field.laske_paikallisesti(
      instance,
      select_related=True,
    )
    # def get_object
  # class LumeFM2OMaare
