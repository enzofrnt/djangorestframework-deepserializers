"""
This model is used to create the package
"""

from setuptools import setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='djangorestframework-deepserializer',
    version='0.1.15',
    packages=['deepserializer'],
    install_requires=[
        'Django',
        'djangorestframework',
    ],
    description='A package to create deep serializer for django rest framework',
    long_description=long_description,
     long_description_content_type="text/markdown",
    author='Horou and Enzo_frnt',
    url='https://github.com/Horou/djangorestframework-deepserializer',
    keywords=["Django", "Django REST Framework", "Deep", "Depth", "serializer", "viewset", "nested", "nested serializer"],
)
