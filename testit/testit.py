from decimal import Decimal
from unittest import expectedFailure

from django.db import models
from django.forms import modelform_factory
from django import test

from .mallit import (
  Asiakas,
  Lasku,
  Osoite,
  Paamies,
  Rivi,
)


class Lume(test.TestCase):
  # pylint: disable=invalid-name, unused-variable

  @classmethod
  def setUpTestData(cls):
    super().setUpTestData()
    asiakas = Asiakas.objects.create(nimi='Asiakas')
    paamies = Paamies.objects.create(nimi='Velkoja')
    Osoite.objects.create(asiakas=asiakas, osoite='Katu 1')
    Osoite.objects.create(asiakas=asiakas, osoite='Katu 123 B 4')
    Osoite.objects.create(asiakas=asiakas, osoite='Katu 456')
    lasku_1 = Lasku.objects.create(asiakas=asiakas, paamies=paamies, numero=1)
    lasku_3 = Lasku.objects.create(asiakas=asiakas, paamies=paamies, numero=3)
    lasku_2 = Lasku.objects.create(asiakas=asiakas, paamies=paamies, numero=2)
    Rivi.objects.create(lasku=lasku_3, summa=123, selite='Samppanjaa')
    Rivi.objects.create(lasku=lasku_3, summa=456, selite='Kaviaaria')
    Rivi.objects.create(lasku=lasku_2, summa=789, selite='Jalokiviä')

  def testaa_paikallinen_laskenta(self):
    asiakas = Asiakas.objects.only('pk').get()
    self.assertEqual(asiakas.pisin_osoite.osoite, 'Katu 123 B 4')
    self.assertTrue(asiakas.useita_laskuja)
    # def testaa_only

  def testaa_refresh_from_db(self):
    asiakas = Asiakas.objects.only('pk').get()
    #asiakas.refresh_from_db('pk')
    print(asiakas.__dict__, asiakas._state.__dict__)
    #raise RuntimeError
    self.assertTrue(asiakas.useita_laskuja)
    # def testaa_refresh_from_db

  def testaa_1x_lume(self):
    '''
    Asiakkaan pisin osoite = Katu 123 B 4?
    '''
    self.assertEqual(
      list(Asiakas.objects.values('pisin_osoite__osoite')),
      [{'pisin_osoite__osoite': 'Katu 123 B 4'}],
    )
    # def testaa_1x_lume

  def testaa_2x_lume(self):
    '''
    Viimeisimmän laskun arvokkaimman rivin selite = Kaviaaria?
    '''
    self.assertEqual(
      list(Asiakas.objects.values('viimeisin_lasku__arvokkain_rivi__selite')),
      [{'viimeisin_lasku__arvokkain_rivi__selite': 'Kaviaaria'}],
    )
    # def testaa_2x_lume

  def testaa_lume_laskenta(self):
    '''
    Viimeisimmän laskun arvokkaimman rivin osuus koko summasta on oikein?
    '''
    self.assertEqual(
      Asiakas.objects.get().viimeisin_lasku.arvokkain_osuus,
      Decimal(456) // Decimal(123+ 456),
    )
    self.assertTrue(
      Asiakas.objects.get().viimeisin_lasku.arvo_yli_500,
    )
    self.assertFalse(
      Asiakas.objects.get().vanhin_lasku.arvo_yli_500,
    )
    # def testaa_lume_laskenta

  @expectedFailure
  def testaa_outerref(self):
    '''
    Niiden laskujen lukumäärä, joiden koko summa on yhdellä rivillä = 1?

    – Lumekenttä OuterRef-viittauksen takaa ei toistaiseksi toimi.
    '''
    self.assertEqual(Lasku.objects.filter(
      models.Exists(
        Rivi.objects.filter(
          lasku=models.OuterRef('pk'),
          summa=models.OuterRef('rivien_summa'),
        )
      )
    ).count(), 1)
    # def testaa_outerref_lume

  def testaa_summa(self):
    '''
    Päämiehen laskujen summa = 1368?
    '''
    self.assertEqual(
      list(Paamies.objects.values('laskujen_summa')),
      [{'laskujen_summa': Decimal('1368')}],
    )
    # def testaa_summa

  def testaa_tallennus(self):
    ''' Toimiiko tallennus lumekenttien estämättä? '''
    asiakas = Asiakas(nimi='Asiakas')
    asiakas.save()
    asiakas.refresh_from_db()
    self.assertEqual(asiakas.viimeisin_lasku, None)
    # def testaa_tallennus

  def testaa_luonti_lomakkeen_kautta(self):
    ''' Toimiiko mallipohjaisen lomakkeen luonti ja tallennus? '''
    asiakas = modelform_factory(Asiakas, fields=['nimi'])(
      data={'nimi': 'Uusi Asiakas'},
    ).save()
    asiakas.refresh_from_db
    # def testaa_luonti_lomakkeen_kautta

  def testaa_paivitys_lomakkeen_kautta(self):
    ''' Toimiiko mallipohjaisen lomakkeen luonti ja tallennus? '''
    asiakas = Asiakas.objects.first()
    modelform_factory(Asiakas, fields=['nimi'])(
      data={'nimi': 'Nimi Vaihdettu'},
      instance=asiakas,
    ).save()
    # def testaa_paivitys_lomakkeen_kautta

  def testaa_valmiiksi_laskettu(self):
    self.assertEqual(
      list(Asiakas.objects.lume('viimeisin_lasku').values_list(
        'viimeisin_lasku__arvokkain_rivi__selite'
      )),
      [('Kaviaaria', ), ]
    )
    # def testaa_valmiiksi_laskettu

  # class Lume
