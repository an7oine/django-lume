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

from django.db import models
from django.db.models.base import DEFERRED
from django.utils.functional import cached_property


class Lumesaate:
  # pylint: disable=no-member

  def __init__(self, *args, **kwargs):
    kysely = kwargs.pop('kysely', None)
    laske = kwargs.pop('laske', None)
    aseta = kwargs.pop('aseta', None)
    automaattinen = kwargs.pop('automaattinen', False)
    assert kysely
    kwargs.update({
      'null': True,
    })
    super().__init__(*args, **kwargs)
    self._kysely = kysely
    self._laske = laske
    self._aseta = aseta
    self.automaattinen = automaattinen
    self.column = None # ei käytetä tietokantataulun saraketta
    # def __init__

  def deconstruct(self):
    name, path, args, kwargs = super().deconstruct()
    return name, path, args, {
      **kwargs,
      'kysely': self.kysely,
    }
    # def deconstruct

  @cached_property
  def kysely(self):
    ''' Hae kyselylauseke (joko lambda tai suora arvo) '''
    return self._kysely() if callable(self._kysely) else self._kysely
    # def kysely

  def laske_paikallisesti(self, rivi):
    '''
    Lasketaan kentän arvo paikallisesti, jos laskentafunktio on määritelty;
    muuten kysytään kenttää erikseen kannasta.
    '''
    if callable(self._laske):
      return self._laske(rivi)
    else:
      return getattr(
        self.model.objects.only(self.name).get(pk=rivi.pk),
        self.name
      )
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

  def lataa_kannasta(self, query):
    '''
    Ladataanko tämän kentän arvo kyselyn yhteydessä? Vastataan seuraavasti:
    - kysely kohdistuu muuhun kuin tähän tauluun: ei ladata
    - `.lume`- tai `.only`-metodia kutsuttu: onko kenttä listalla?
    - `.defer`-metodia kutsuttu: onko kenttä `automaattinen` eikä listalla?
    - onko kenttä `automaattinen`?
    '''
    if query.model is not self.model:
      return False
    kentat, defer = query.deferred_loading
    pyydetyt_lumekentat = getattr(query, 'pyydetyt_lumekentat', None)
    if pyydetyt_lumekentat is not None:
      return self.name in pyydetyt_lumekentat
    return (
      not defer and self.name in kentat
    ) or (
      self.automaattinen and defer and self.name not in kentat
    )
    # def lataa_kannasta

  def contribute_to_class(self, cls, *args, **kwargs):
    '''
    Lisätään tietokantamalliin ominaisuuskuvaaja (Descriptor)
    lumekenttien käsittelyä varten.
    '''
    super(Lumesaate, self).contribute_to_class(cls, *args, **kwargs)
    kentta = self
    class Lumeominaisuus(models.query_utils.DeferredAttribute):
      def __init__(self, field_name):
        super(Lumeominaisuus, self).__init__(field_name)
        self.lume_ohitettu_avain = '_lume_ohitettu_' + field_name
        # def __init__
      def __get__(self, instance, cls=None):
        '''
        Kysyttäessä kenttää, jota ei luettu kannasta,
        haetaan sen arvo `laske_paikallisesti`-metodin avulla.
        '''
        if instance is None:
          return self
        data = instance.__dict__
        if data.get(self.field_name, self) is self:
          val = self._check_parent_chain(instance, self.field_name)
          if val is None:
            val = kentta.laske_paikallisesti(instance)
            # Poista aiempi merkintä ohitetusta kentästä.
            del data[self.lume_ohitettu_avain]
          data[self.field_name] = val
        return data[self.field_name]
        # def __get__
      def __set__(self, instance, value):
        '''
        Ohitetaan {DEFERRED}-arvot kannasta alustettaessa;
        jos aiempaa kentän arvoa muutetaan,
        kutsutaan `aseta_paikallisesti`-metodia.
        '''
        if instance is None:
          return
        data = instance.__dict__
        if value == str(DEFERRED):
          # Jos kannasta saadaan paluuarvona vain tieto ohitetusta kentästä,
          # jätetään rivin tietoihin merkintä tästä.
          data[self.lume_ohitettu_avain] = True
        elif data.get(self.field_name, self) is not self \
        or data.get(self.lume_ohitettu_avain, False):
          # Jos kentän arvo on asetettu jo aiemmin
          # tai kannasta ei saatu kentän arvoa,
          # kutsu kenttäkohtaisesti määritettyä `aseta`-funktiota.
          kentta.aseta_paikallisesti(instance, value)
        else:
          # Kun kentän arvo haetaan kannasta, asetetaan normaalisti.
          data[self.field_name] = value
        # def __set__
      # class Lumeominaisuus
    setattr(cls, self.attname, Lumeominaisuus(self.attname))
    # def contribute_to_class

  def get_joining_columns(self, reverse_join=False):
    ''' Ohita normaali JOIN-ehto (`a`.`id` = `b`.`a_id`) '''
    # pylint: disable=unused-argument
    return tuple()
    # def get_joining_columns

  def get_extra_restriction(self, where_class, alias, related_alias):
    ''' Luo JOIN-ehto muotoa (`a`.`id` = (SELECT ... from `b`)) '''
    # pylint: disable=unused-argument
    rhs_field = self.related_fields[0][1]
    field = rhs_field.model._meta.get_field(rhs_field.column)

    class Lookup(field.get_lookup('exact')):
      def process_rhs(self2, compiler, connection):
        # pylint: disable=no-self-argument, unused-argument
        if self.lataa_kannasta(compiler.query):
          sql, params = compiler.compile(self2.rhs.resolve_expression(
            query=compiler.query
          ))
          return '(' + sql + ')', params
        else:
          # Palautetaan kysely, jonka mukainen liitostaulu jää tyhjäksi.
          return 'NULL', []
        # def process_rhs
      # class Lookup

    return Lookup(field.get_col(alias), self.kysely)
    # def get_extra_restriction

  def select_format(self, compiler, sql, params):
    ''' Palauta SELECT-lauseke '''
    # pylint: disable=unused-argument
    if self.lataa_kannasta(compiler.query):
      return self.kysely.resolve_expression(
        query=compiler.query
      ).as_sql(
        compiler, compiler.connection
      )
    else:
      # Palautetaan kysely, joka tunnistetaan ohitetuksi arvoksi.
      return '%s', [DEFERRED]
    # def select_format

  # class Lumesaate
