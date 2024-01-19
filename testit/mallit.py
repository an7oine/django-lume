from django.db import models

import lume


class Asiakas(models.Model):
  nimi = models.CharField(max_length=255)
  pisin_osoite = lume.ForeignKey( # pylint: disable=no-member
    'Osoite',
    on_delete=models.DO_NOTHING,
    related_name='+',
    kysely=lambda: models.Subquery(
      Osoite.objects.filter(
        asiakas=models.OuterRef('pk'),
      ).annotate(
        osoitteen_pituus=models.Func('osoite', function='LENGTH'),
      ).order_by('-osoitteen_pituus').values('pk')[:1],
      output_field=models.IntegerField()
    ),
    null=True,
    laske=lambda rivi: next(
      (rivi[0] for rivi in sorted(
        rivi.osoitteet.values_list(
          'pk', 'osoite'
        ),
        key=lambda o: len(o[1]),
        reverse=True
      )),
      None
    ),
  )
  vanhin_lasku = lume.ForeignKey( # pylint: disable=no-member
    'Lasku',
    on_delete=models.DO_NOTHING,
    related_name='+',
    kysely=lambda: models.Subquery(
      Lasku.objects.filter(
        asiakas=models.OuterRef('pk'),
      ).order_by('numero').values('pk')[:1],
      output_field=models.IntegerField()
    ),
    laske=lambda rivi: next(
      (rivi[0] for rivi in sorted(
        rivi.laskut.values_list(
          'pk', 'numero'
        ),
        key=lambda o: o[1],
      )),
      None
    ),
    null=True,
  )
  viimeisin_lasku = lume.ForeignKey( # pylint: disable=no-member
    'Lasku',
    on_delete=models.DO_NOTHING,
    related_name='+',
    kysely=lambda: models.Subquery(
      Lasku.objects.filter(
        asiakas=models.OuterRef('pk'),
      ).order_by('-numero').values('pk')[:1],
      output_field=models.IntegerField()
    ),
    null=True,
    laske=lambda rivi: next(
      (rivi[0] for rivi in sorted(
        rivi.laskut.values_list(
          'pk', 'numero'
        ),
        key=lambda o: o[1],
        reverse=True
      )),
      None
    ),
  )
  useita_laskuja = lume.BooleanField( # pylint: disable=no-member
    kysely=~models.Q(viimeisin_lasku=models.F('vanhin_lasku')),
    laske=lambda rivi: rivi.viimeisin_lasku != rivi.vanhin_lasku,
  )

class Osoite(models.Model):
  asiakas = models.ForeignKey(
    Asiakas, related_name='osoitteet', on_delete=models.CASCADE
  )
  osoite = models.CharField(max_length=255)

class Paamies(models.Model):
  nimi = models.CharField(max_length=255)
  laskujen_summa = lume.DecimalField( # pylint: disable=no-member
    max_digits=11,
    decimal_places=2,
    kysely=lambda: models.Subquery(
      Rivi.objects.filter(
        lasku__paamies=models.OuterRef('pk'),
      ).order_by('lasku__paamies').values('lasku__paamies').values(
        summa_yht=models.Sum('summa'),
      ),
      output_field=models.DecimalField(),
    ),
  )

class Lasku(models.Model):
  asiakas = models.ForeignKey(
    Asiakas, related_name='laskut', on_delete=models.CASCADE
  )
  paamies = models.ForeignKey(Paamies, on_delete=models.CASCADE)
  numero = models.IntegerField()
  arvokkain_rivi = lume.ForeignKey( # pylint: disable=no-member
    'Rivi',
    on_delete=models.DO_NOTHING,
    related_name='+',
    kysely=lambda: models.Subquery(
      Rivi.objects.filter(
        lasku=models.OuterRef('pk'),
      ).order_by(
        '-summa'
      ).values(
        'lasku'
      ).values(
        'pk'
      ),
      output_field=models.IntegerField()
    ),
    null=True,
  )
  rivien_summa = lume.DecimalField( # pylint: disable=no-member
    max_digits=11,
    decimal_places=2,
    kysely=lambda: models.Subquery(
      Rivi.objects.filter(
        lasku=models.OuterRef('pk'),
      ).values(
        'lasku',
      ).order_by(
        'lasku'
      ).values(
        summa_yht=models.Sum('summa'),
      ),
      output_field=models.DecimalField(),
    ),
  )
  arvokkain_osuus = lume.DecimalField( # pylint: disable=no-member
    max_digits=3,
    decimal_places=2,
    kysely=models.F('arvokkain_rivi__summa') / models.F('rivien_summa'),
  )
  arvo_yli_500 = lume.BooleanField(
    kysely=models.Q(rivien_summa__gte=500),
    laske=lambda rivi: (
      rivi.rivien_summa is not None
      and rivi.rivien_summa >= 500
    ),
  )

class Rivi(models.Model):
  lasku = models.ForeignKey(Lasku, on_delete=models.CASCADE)
  summa = models.DecimalField(max_digits=11, decimal_places=2)
  selite = models.CharField(max_length=255)
