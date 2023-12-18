"""
This model is used to create the package
"""

from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='djangorestframework-deepserializer',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Django',
        'djangorestframework',
    ],
    description='A package to create deep serializer for django rest framework',
    long_description=long_description,
    author='Horou and Enzo_frnt',
    url='https://github.com/Horou/djangorestframework-deepserializer'
)
