# -*- coding: utf-8 -*-

import functools

from django import VERSION as django_versio
from django.db import models
from django.utils.functional import cached_property, classproperty

from .maare import Lumemaare, LumeFM2OMaare
from .sarake import Lumesarake


EI_ASETETTU = object()


class Lumekentta(models.fields.Field):

  @classproperty
  def forward_related_accessor_class(cls):
    # pylint: disable=no-self-argument, invalid-name, no-member
    # Huomaa, että super-toteutusta ei ole määritelty kaikille kenttätyypeille.
    # Tällaisen kentän tapauksessa kutsuvaan koodiin nousee AttributeError.
    @functools.wraps(super().forward_related_accessor_class, updated=())
    class forward_related_accessor_class(
      LumeFM2OMaare,
      super().forward_related_accessor_class
    ): pass
    return forward_related_accessor_class
    # def forward_related_accessor_class

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

  def formfield(self, **kwargs):
    ''' Nollataan lomakkeelle annettu `initial`-arvo (EI_ASETETTU). '''
    return super().formfield(**{**kwargs, 'initial': None})

  @property
  def kysely(self):
    ''' Hae kyselylauseke (joko lambda tai suora arvo) '''
    return self._kysely() if callable(self._kysely) else self._kysely
    # def kysely
  @kysely.setter
  def kysely(self, kysely):
    self._kysely = kysely
    # def kysely

  def laske_paikallisesti(self, rivi, select_related=False):
    '''
    Lasketaan kentän arvo paikallisesti, jos
    - laskentafunktio on määritelty; ja
    - laskentafunktio palauttaa muun arvon kuin EI_ASETETTU.

    Muuten kysytään kenttää erikseen kannasta.

    Parametrillä `select_related=True` palautetaan kokonainen, viitattu
    (M2O tai O2O) rivi kannasta.
    '''
    # pylint: disable=protected-access
    if callable(self._laske):
      arvo = self._laske(rivi)
      if arvo is not EI_ASETETTU:
        if select_related:
          return arvo
        return getattr(arvo, 'pk', arvo)
      # if callable

    # Kysytään erikseen kannasta.
    # Vrt. `django.db.models.Model.refresh_from_db`.
    qs = rivi.__class__._base_manager.db_manager(
      None, hints={'instance': rivi}
    ).filter(pk=rivi.pk).only(self.attname)
    # Ei toimi toistaiseksi.
    #if select_related:
    #  qs = qs.select_related(self.name)
    try:
      #return getattr(qs.get(), self.name if select_related else self.attname)
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

  def get_extra_restriction(self, alias, related_alias):
    '''
    Luo JOIN-ehto muotoa (`a`.`id` = (SELECT ... from `b`)).

    Tätä kutsutaan vain `ForeignObject`-tyyppiselle kentälle.

    Huomaa erilliset kutsukäytännöt (parametrien lukumäärä)
    Django-versioilla 3.2 / 4.0.
    '''
    # pylint: disable=unused-argument, no-member
    rhs_field = self.related_fields[0][1]
    field = rhs_field.model._meta.get_field(rhs_field.column)
    return field.get_lookup('exact')(
      self.get_col(related_alias),
      field.get_col(alias),
    )
    # def get_extra_restriction

  if django_versio < (4, 0):
    # pylint: disable=function-redefined, no-member, unused-argument
    # Hyväksytään aiemmin käytössä ollut `where_class`-parametri.
    @functools.wraps(get_extra_restriction)
    def get_extra_restriction(self, where_class, alias, related_alias):
      return __class__.get_extra_restriction.__wrapped__(
        self, alias, related_alias
      )

  # class Lumekentta
