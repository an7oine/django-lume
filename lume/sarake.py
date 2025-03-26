# -*- coding: utf-8 -*-

from django.db import models


class Lumesarake(models.expressions.Col):
  '''
  Sarakeluokka, jonka arvo lasketaan kentälle määritetyn kyselyn mukaan.
  '''
  # pylint: disable=abstract-method

  def as_sql(self, compiler, connection):
    ''' Muodosta SELECT-lauseke ja siihen liittyvät SQL-parametrit. '''
    # pylint: disable=unused-argument
    join = compiler.query.alias_map.get(self.alias)
    if isinstance(join, models.sql.datastructures.Join):
      # Liitostaulu: muodosta alikysely tähän tauluun,
      # rajaa kysytty rivi liitostaulun primääriavaimen mukaan.
      return compiler.compile(
        models.Subquery(
          self.target.model.objects.filter(
            pk=models.expressions.RawSQL(
              '%s.%s' % (
                compiler.quote_name_unless_alias(join.table_alias),
                connection.ops.quote_name(self.target.model._meta.pk.get_attname()),
              ), ()
            ),
          ).values(**{
            # Käytetään kentän nimestä poikkeavaa aliasta.
            f'_{self.target.name}_join': self.target.kysely,
          }),
          output_field=self.field,
        ).resolve_expression(query=compiler.query)
      )
      # if isinstance(join, Join)

    elif isinstance(join, models.sql.datastructures.BaseTable):
      # Kyselyn aloitustaulu: suora kysely.
      return compiler.compile(self.target.kysely.resolve_expression(
        query=compiler.query
      ))
      # elif isinstance (join, BaseTable)

    elif join is None:
      raise NotImplementedError(f'{join!r} is None')

    else:
      # Muita kyselytyyppejä ei tueta.
      raise NotImplementedError(
        f'not isinstance({join!r}, (BaseTable, Join))'
      )
    # def as_sql

  # class Lumesarake
