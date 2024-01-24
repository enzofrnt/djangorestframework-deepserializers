 djangorestframework-deepserializer

## Description

`djangorestframework-deepserializer` is a Django REST framework package that provides deep serialization of nested JSON. It supports various types of relationships including `one_to_one`, `one_to_many`, `many_to_one`, `many_to_many`, and also in reverse through their `related_name`. This package is particularly useful when you need to serialize your models in a complex way.

## Installation

You can install `djangorestframework-deepserializer` using pip:

```bash
pip install djangorestframework-deepserializer
```

## Usage

After installing the package, you can use it to create deep serializers for your Django models. This will allow you to serialize your models along with all their related models, providing a comprehensive view of your data.

Here’s a basic example of how to use djangorestframework-deepserializer:

Python

from deepserializer import DeepSerializer
from myapp.models import MyModel

class MyModelSerializer(DeepSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'

In this example, MyModelSerializer will serialize instances of MyModel along with all related models.

Deep Serialization

Deep serialization is the process of serializing a model along with all its related models. This is done recursively, meaning that the related models of the related models are also serialized, and so on. This allows you to get a complete view of your data in a single serialized object.

The types of relationships that are supported include:

one_to_one: One instance of a model is related to one instance of another model.
one_to_many: One instance of a model is related to many instances of another model.
many_to_one: Many instances of a model are related to one instance of another model.
many_to_many: Many instances of a model are related to many instances of another model.

and in reverse with:
related_name: The name to use for the relation from the related object back to this one.

## Contributing

Contributions are welcome! Please read the contributing guidelines before getting started.

## License

This project is licensed under the terms of the MIT license.
