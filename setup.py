# -*- coding: utf-8 -*-

import setuptools

setuptools._install_setup_requires({'setup_requires': ['git-versiointi']})
from versiointi import asennustiedot

setuptools.setup(
  name='django-lume',
  description='Django-tuki lume- eli näennäiskentille',
  url='https://git.pispalanit.fi/pit/django-lume',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@pispalanit.fi',
  packages=setuptools.find_packages(),
  include_package_data=True,
  zip_safe=False,
  **asennustiedot(__file__)
)
