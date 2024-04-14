"""
This model is used to create the package
"""

from setuptools import setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='djangorestframework-deepserializers',
    version='0.1',
    packages=['deepserializer'],
    install_requires=[
        'Django',
        'djangorestframework',
    ],
    description='A package to create deep Serializers and ModelViewSet for django rest-framework',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Made by enzo_frnt from the Horou repo',
    url='https://github.com/enzofrnt/djangorestframework-deepserializers',
    keywords=["Django", "Django REST Framework", "Deep", "Depth", "serializer", "viewset", "nested", "nested serializer"],
)
