# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
  setup_requires='git-versiointi>=1.6rc4',
  name='django-lume',
  description='Django-tuki lume- eli näennäiskentille',
  url='https://github.com/an7oine/django-lume.git',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@pispalanit.fi',
  packages=find_packages(),
  include_package_data=True,
  zip_safe=False,
  install_requires='Django>=4.2',
)
