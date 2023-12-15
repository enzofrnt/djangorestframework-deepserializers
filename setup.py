"""
This model is used to create the package
"""

from setuptools import setup, find_packages

setup(
    name='deep_serializer_for_django',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Django',
        'djangorestframework',
    ],
)
