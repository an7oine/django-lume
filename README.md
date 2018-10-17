django-lume
===========

Django-tuki muiden kenttien mukaan tietokannassa laskettaville lume- eli näennäiskentille

# Asennus

```bash
$ pip install -e git+git://git@git.pispalanit.fi:pit/django-lume.git
```

Lisää `lume` asennettuihin sovelluksiin:
```python
INSTALLED_APPS += ['lume']
```

# Käyttö

Lisää kunkin mallin kenttiin halutut näennäiskentät:
```python
class Malli(models.Model):
  ...
  kentta = lume.Kentta(
    models.Subquery(
      ToinenMalli.objects.filter(
        viittaus=models.OuterRef('pk')
      ).annotate(
        ...
      ).values(...),
      output_field=...
    ),
    laske=lambda self: self.toisen_mallin_kohteita_yhteensa(),
    automaattinen=True,
  )
  ...
```

Automaattisiksi määritetyt näennäiskentät lisätään kaikkiin kyselyihin. Muu kuin automaattinen kenttä voidaan lisätä kyselyyn tarvittaessa käyttämällä `QuerySet`-luokan metodia `lume('kentän nimi')`, esim.
```python
qs = Malli.objects.filter(...).lume('kentta2', 'kentta3')
```

Ei-automaattinen näennäiskenttä, jota ei ole lisätty em. mukaisesti kyselyyn, lasketaan kullekin riville erikseen `laske`-parametrin avulla määritetyn funktion mukaisesti.
