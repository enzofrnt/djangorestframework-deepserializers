from setuptools import setup, find_packages

setup(
    name='deepSerializerforDjango',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'Django',
        'djangorestframework',
    ],
)