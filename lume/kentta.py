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

from django.db import models

class Lumekentta:

  def __init__(self, kysely, laske=None, automaattinen=True):
    super().__init__()
    self.kysely = kysely
    self.laske = laske
    self.automaattinen = automaattinen
    # def __init__

  # class Lumekentta
