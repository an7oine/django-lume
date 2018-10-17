# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
  name='django-lume',
  version='1.0.0',
  description='Django-tuki lume- eli näennäiskentille',
  url='https://git.pispalanit.fi/pit/django-lume',
  author='Antti Hautaniemi',
  author_email='antti.hautaniemi@pispalanit.fi',
  packages=find_packages(),
  include_package_data=True,
  install_requires=[
    'Django>=2.0',
  ],
  zip_safe=False
)
