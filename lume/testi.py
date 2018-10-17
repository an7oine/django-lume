# -*- coding: utf-8 -*-

from decimal import Decimal
from unittest import expectedFailure

from django.db import connection, models
from django import test

import lume


class Testimalli(models.Model):
  class Meta:
    abstract = True
    app_label = '_lume_testi'

class Asiakas(Testimalli):
  nimi = models.CharField(max_length=255)
  pisin_osoite = lume.ForeignKey( # pylint: disable=no-member
    'Osoite', on_delete=models.DO_NOTHING,
    kysely=lambda: models.Subquery(
      Osoite.objects.filter(
        asiakas=models.OuterRef('pk'),
      ).order_by('-osoite__len').values('pk')[:1],
      output_field=models.IntegerField()
    ),
    null=True,
  )
  viimeisin_lasku = lume.ForeignKey( # pylint: disable=no-member
    'Lasku', on_delete=models.DO_NOTHING,
    kysely=lambda: models.Subquery(
      Lasku.objects.filter(
        asiakas=models.OuterRef('pk'),
      ).order_by('-numero').values('pk')[:1],
      output_field=models.IntegerField()
    ),
    null=True,
  )

class Osoite(Testimalli):
  asiakas = models.ForeignKey(Asiakas, on_delete=models.CASCADE)
  osoite = models.CharField(max_length=255)

class Paamies(Testimalli):
  nimi = models.CharField(max_length=255)
  laskujen_summa = lume.DecimalField( # pylint: disable=no-member
    kysely=lambda: models.Subquery(
      Rivi.objects.filter(
        lasku__paamies=models.OuterRef('pk'),
      ).order_by('lasku__paamies').values('lasku__paamies').values(
        summa_yht=models.Sum('summa'),
      ),
      output_field=models.DecimalField(),
    ),
  )

class Lasku(Testimalli):
  asiakas = models.ForeignKey(Asiakas, on_delete=models.CASCADE)
  paamies = models.ForeignKey(Paamies, on_delete=models.CASCADE)
  numero = models.IntegerField()
  arvokkain_rivi = lume.ForeignKey( # pylint: disable=no-member
    'Rivi', on_delete=models.DO_NOTHING,
    kysely=lambda: models.Subquery(
      Rivi.objects.filter(
        lasku=models.OuterRef('pk'),
      ).order_by('-summa').values('pk')[:1],
      output_field=models.IntegerField()
    ),
    null=True,
  )
  rivien_summa = lume.DecimalField( # pylint: disable=no-member
    kysely=lambda: models.Subquery(
      Rivi.objects.filter(
        lasku=models.OuterRef('pk'),
      ).order_by('lasku').values(
        summa_yht=models.Sum('summa'),
      ),
      output_field=models.DecimalField(),
    ),
  )

class Rivi(Testimalli):
  lasku = models.ForeignKey(Lasku, on_delete=models.CASCADE)
  summa = models.DecimalField(max_digits=11, decimal_places=2)
  selite = models.CharField(max_length=255)


migrations = '''
CREATE TABLE IF NOT EXISTS `_lume_testi_paamies` (
  `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `nimi` varchar(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS `_lume_testi_asiakas` (
  `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `nimi` varchar(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS `_lume_testi_asiakasosoite` (
  `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `osoite` varchar(255) NOT NULL, `asiakas_id` integer NOT NULL,
  CONSTRAINT `_lume_testi_asiakasosoite_asiakas_id_4487f9e9_fk__lume_testi_asi`
  FOREIGN KEY (`asiakas_id`) REFERENCES `_lume_testi_asiakas` (`id`)
);
CREATE TABLE IF NOT EXISTS `_lume_testi_lasku` (
  `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `numero` integer NOT NULL,
  `asiakas_id` integer NOT NULL,
  `paamies_id` integer NOT NULL,
  CONSTRAINT `_lume_testi_lasku_paamies_id_82ff7002_fk__lume_testi_paa`
  FOREIGN KEY (`paamies_id`) REFERENCES `_lume_testi_paamies`(`id`),
  CONSTRAINT `_lume_testi_lasku_asiakas_id_d2497145_fk__lume_testi_asi`
  FOREIGN KEY (`asiakas_id`) REFERENCES `_lume_testi_asiakas` (`id`)
);
CREATE TABLE IF NOT EXISTS `_lume_testi_rivi` (
  `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `summa` numeric(11, 2) NOT NULL, `selite` varchar(255) NOT NULL,
  `lasku_id` integer NOT NULL,
  CONSTRAINT `_lume_testi_rivi_lasku_id_01d67aff_fk__lume_testi_l`
  FOREIGN KEY (`lasku_id`) REFERENCES `_lume_testi_lasku` (`id`)
);
''', '''
DROP TABLE IF EXISTS `_lume_testi_asiakasosoite`;
DROP TABLE IF EXISTS `_lume_testi_rivi`;
DROP TABLE IF EXISTS `_lume_testi_paamies`;
DROP TABLE IF EXISTS `_lume_testi_lasku`;
DROP TABLE IF EXISTS `_lume_testi_asiakas`;
'''


class Testi(test.TestCase):
  # pylint: disable=invalid-name, unused-variable

  @classmethod
  def setUpTestData(cls):
    super().setUpTestData()
    with connection.cursor() as cursor:
      cursor.execute(migrations[0])
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
    Rivi.objects.create(lasku=lasku_1, summa=789, selite='Jalokiviä')

  @classmethod
  def tearDownTestData(cls):
    with connection.cursor() as cursor:
      cursor.execute(migrations[1])
    # def tearDownTestData

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
    # def testaa_2x_lume

  # class Testi
