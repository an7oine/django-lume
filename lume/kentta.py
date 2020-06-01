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
# pylint: disable=invalid-name, useless-object-inheritance

from django.db import models


__VIITTAUKSEN_TAKAA__ = '__VIITTAUKSEN_TAKAA__'


class Lumesaate:
  # pylint: disable=no-member

  def __init__(
    self, *args,
    kysely, laske=None, aseta=None, automaattinen=False,
    _toimii_viittauksen_takaa=False,
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
    kwargs.setdefault('default', models.DEFERRED)

    # Lisää super-kutsuun parametri `editable=False`,
    # jos `aseta`-funktiota ei ole määritetty.
    if not aseta:
      kwargs['editable'] = False

    super().__init__(*args, **kwargs)
    self._kysely = kysely
    self._laske = laske
    self._aseta = aseta
    self.automaattinen = automaattinen

    self._toimii_viittauksen_takaa = _toimii_viittauksen_takaa

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
    if callable(self._laske):
      return self._laske(rivi)
    else:
      return self.model.objects.filter(pk=rivi.pk).values_list(
        self.name, flat=True
      ).first()
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

  def contribute_to_class(self, cls, *args, **kwargs):
    '''
    Lisätään tietokantamalliin ominaisuuskuvaaja (Descriptor)
    lumekenttien käsittelyä varten.
    '''
    super().contribute_to_class(cls, *args, **kwargs)
    kentta = self
    class Lumeominaisuus(models.query_utils.DeferredAttribute):
      def __get__(self, instance, cls=None):
        '''
        Kysyttäessä kenttää, jota ei luettu kannasta,
        haetaan sen arvo `laske_paikallisesti`-metodin avulla.
        '''
        if instance is None:
          return self
        data = instance.__dict__
        field_name = self.field.attname
        if field_name not in data:
          val = self._check_parent_chain(instance)
          if val is None:
            val = kentta.laske_paikallisesti(instance)
          data[field_name] = val
        return data[field_name]
        # def __get__
      def __set__(self, instance, value):
        '''
        Jos kentän arvo asetetaan suoraan kutsuvasta koodista,
        kutsutaan `aseta_paikallisesti`-metodia.
        '''
        if instance is None or value == __VIITTAUKSEN_TAKAA__:
          return
        data = instance.__dict__
        field_name = self.field.attname
        if not instance.pk:
          # Uudelle riville asetetaan arvo paikallisesti.
          # Asetetaan sitten rividataan.
          kentta.aseta_paikallisesti(instance, value)
          data[field_name] = value
        elif field_name not in data:
          # Kun arvo ladataan ensimmäisen kerran kannasta,
          # asetetaan normaalisti datasanakirjaan.
          data[field_name] = value
        elif data.get(field_name) == value:
          # Jos arvo ei muutu, ei tehdä mitään.
          # Muuten mm. `django.db.models.query.ModelIterable.__iter__` kaatuu.
          pass
        else:
          # Jos kentän arvo on asetettu jo aiemmin,
          # kutsutaan kenttäkohtaisesti määritettyä `aseta`-funktiota
          # ja asetetaan sen jälkeen datasanakirjaan.
          kentta.aseta_paikallisesti(instance, value)
          data[field_name] = value
        # def __set__
      # class Lumeominaisuus
    setattr(cls, self.attname, Lumeominaisuus(self))
    # def contribute_to_class

  def get_joining_columns(self, reverse_join=False):
    ''' Ohita normaali JOIN-ehto (`a`.`id` = `b`.`a_id`) '''
    # pylint: disable=unused-argument
    return tuple()
    # def get_joining_columns

  def get_extra_restriction(self, where_class, alias, related_alias):
    '''
    Luo JOIN-ehto muotoa (`a`.`id` = (SELECT ... from `b`)).

    Viittauksen takaa (mikäli alkuperäinen kysely kohdistuu muuhun
    kuin nykyiseen malliin) palautetaan tyhjä JOIN-ehto.
    '''
    # pylint: disable=unused-argument
    rhs_field = self.related_fields[0][1]
    field = rhs_field.model._meta.get_field(rhs_field.column)

    class Lookup(field.get_lookup('exact')):
      def process_rhs(self2, compiler, connection):
        # pylint: disable=no-self-argument, unused-argument
        # pylint: disable=protected-access
        if self._toimii_viittauksen_takaa \
        or compiler.query.model is self.model:
          sql, params = compiler.compile(self2.rhs.resolve_expression(
            query=compiler.query
          ))
          return '(' + sql + ')', params
        else:
          return 'NULL', []
        # def process_rhs
      # class Lookup

    return Lookup(field.get_col(alias), self.kysely)
    # def get_extra_restriction

  def sql_select(self, compiler):
    '''
    Palauta SELECT-lauseke.
    Tätä kutsutaan `Col.as_sql`-metodista (ks. `puukko.py`).

    Huom. viittauksen takaa haettavat lumekentät eivät toimi oikein,
    joten palautetaan niiden sijaan erityinen `VIITTAUKSEN_TAKAA`-merkintä.
    '''
    if self._toimii_viittauksen_takaa \
    or compiler.query.model is self.model:
      return compiler.compile(self.kysely.resolve_expression(
        query=compiler.query
      ))
    else:
      return f"'{__VIITTAUKSEN_TAKAA__}'", []
    # def sql_select

  # class Lumesaate
