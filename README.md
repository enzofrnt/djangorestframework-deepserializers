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

If you just want to have a API for your model:
urls.py:
```
from deepserializer import DeepViewSet
from myapp.models import User, Group, Tag

router = Router()
DeepViewSet.init_router(router, [
    User,
    Group,
    Tag
])
```
It will create the corresponding serializer and viewsets, you can also make it read_only  by importing ReadOnlyDeepViewSet instead of DeepViewSet

If you want to do a deep serialization:
urls.py:
```
from deepserializer import DeepViewSet
from myapp.models import User, Group, Tag

class DeepUserViewSet(DeepViewSet):
    queryset = User.objects
    use_case = "DeepCreation"

    def create(self, request, *args, **kwargs):
        results = self.get_serializer().deep_update_or_create(User, request.data)
        if any("ERROR" in item for item in results if isinstance(item, dict)):
            return Response(results, status=status.HTTP_409_CONFLICT)
        return Response(results, status=status.HTTP_201_CREATED)
```
The viewset will automaticaly create a serializer if this one doesn't exist

If you want to do a deep serialization that will also delete the previews unused nested objects:
urls.py:
'''
from deepserializer import DeepViewSet
from myapp.models import User, Group, Tag, Alias

class ReplaceAliasDeepUserViewSet(DeepViewSet):
    queryset = User.objects

    def create(self, request, *args, **kwargs):
        results = self.get_serializer().deep_update_or_create(User, request.data, delete_models=[Alias])
        if any("ERROR" in item for item in results if isinstance(item, dict)):
            return Response(results, status=status.HTTP_409_CONFLICT)
        return Response(results, status=status.HTTP_201_CREATED)
'''

The DeepViewSet retrieve the corresponding serializer with get_serializer_class() by using the use_case of the viewset and the queryset model.
With no use_case defined, it will retrieve the default serializer for this model.

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
