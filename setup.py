# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

__import__('setuptools')._install_setup_requires(dict(
  setup_requires=['git-versiointi'],
  dependency_links=[
    'git+ssh://git@git.pispalanit.fi/pit/git-versiointi.git#egg=git-versiointi'
  ],
))
from versiointi import asennustiedot

setup(
  name='django-lume',
  description='Django-tuki lume- eli näennäiskentille',
  url='https://git.pispalanit.fi/pit/django-lume',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@pispalanit.fi',
  packages=find_packages(),
  include_package_data=True,
  zip_safe=False,
  **asennustiedot(__file__)
)
