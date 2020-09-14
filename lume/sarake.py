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
# @created     12.09.2020
# @author      Antti Hautaniemi <antti.hautaniemi@pispalanit.fi>
# @copyright   Copyright (c) Pispalan Insinööritoimisto Oy
# @license     All rights reserved
#============================================================================

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
                connection.ops.quote_name(self.target.model._meta.pk.attname),
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

    else:
      # Muita kyselytyyppejä ei tueta.
      raise NotImplementedError
    # def as_sql

  # class Lumesarake
