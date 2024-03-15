# DeepSerializer

Another Django REST framework addon for those who don't have time.

## Introduction

`djangorestframework-deepserializer` is a Django REST framework package that provides deep serialization of nested JSON. It supports various types of relationships including `one_to_one`, `one_to_many`, `many_to_one`, `many_to_many`, and also in reverse through their `related_name`. All the database calls are already optimized to the maximum using prefetch_related, select_related and some powerful algo without losing any DRF functionality.This package is particularly useful if you really don't want to work.
This projects presume that you already have some or all your django models completed.

## Installation

You can install `djangorestframework-deepserializer` using pip:

```bash
pip install djangorestframework-deepserializer
```

## Usage

### For ultra-fast development.
If you just want to have an API ready for your model.

`models.py`
```Python
from django.db import models

class Image(models.Model):
    id = models.IntegerField(primary_key=True, editable=False)
    url = models.CharField(max_length=200)

class Tag(models.Model):
    name = models.CharField(primary_key=True)
    description = models.TextField(max_length=4000)


class Book(models.Model):
    title = models.CharField(primary_key=True)
    description = models.TextField(max_length=4000)
    tags = models.ManyToManyField(Tag)
    cover = models.ForeignKey(Image, on_delete=models.CASCADE, blank=True, null=True, related_name="books")


class Chapter(models.Model):
    class Meta:
        unique_together = (('book', 'number'),)
    id = models.CharField(primary_key=True, editable=False)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    number = models.IntegerField(default=0)
    content = models.TextField()

    def save(self, *args, **kwargs):
        self.id = "_".join(
            str(getattr(self, field).pk if isinstance(getattr(self, field), models.Model) else getattr(self, field))
            for field in self._meta.unique_together[0]
        )
        super().save(*args, **kwargs)
```

`urls.py`
```Python
from rest_framework import routers
from deepserializer import DeepViewSet
from myapp.models import Book, Chapter, Tag

router = routers.DefaultRouter()
DeepViewSet.init_router(router, [
    Book,
    Chapter,
    Tag
])
```
If you need the read only ViewSets version, replace DeepViewSet with ReadOnlyDeepViewSet

The `init_router` function will create all the necessary ViewSets and Serializers for The given models and will register them in the router.

### For ultra-fast development, with a bit of control.
If you need one of the serializer to act in a specific way, for example also return the number of chapter, you can write your own:

`serializers.py`
```Python
from rest_framework import serializers
from deepserializer import DeepSerializer
from myapp.models import Book, Chapter, Tag

class BookSerializer(DeepSerializer):
    class Meta:
        model = Book
        depth = 10
        fields = '__all__'
        # use_case = "" # by default the use_case is an empty string

    chapters_count = serializers.SerializerMethodField()

    def get_chapters_count(self, obj):
        return len(obj.chapters)
```
This serializer, because of the absence of `use_case` inside the Meta class, will be considered the main serializer for this model and will automatically be retrieved when this model need a serializer.

`urls.py`
```Python
from rest_framework import routers
from deepserializer import DeepViewSet
from myapp.models import Book, Chapter, Tag
from myapp.serializers import * # is needed to allow DeepViewSet to load the serializer in its dict of serializers

router = routers.DefaultRouter()
router.register("Book", DeepViewSet.get_view(Book), basename="Book")
```
The Serializer used for the Book model will be BookSerializer, and this at any depth.

### For ultra-fast development, with even more control.
If you need one of the viewsets to act in a specific way, for example using one serializer for list and another for the rest, you can write your own:

`serializers.py`
```Python
.
.
.

class NoInfoBookSerializer(DeepSerializer):
    class Meta:
        model = Book
        depth = 0
        fields = ("title", "description")
        use_case = "NoInfo"
```

`views.py`
```Python
from deepserializer import DeepViewSet

from myapp.models import Book
from myapp.serializers import NoInfoBookSerializer

class BookViewSets(DeepViewSet):
    queryset = Book.objects

    def get_serializer_class(self):
        if hasattr(self, 'action') and self.action == 'list':
            # return DeepSerializer.get_serializer_class(self.queryset.model, use_case="NoInfo")  # will do the same thing, importing it this way will protect against circular import
            return NoInfoBookSerializer
        return NoInfoBookSerializer.get_serializer_class(self.queryset.model) # this will retrieve BookSerializer without having to manually import it
```
This viewsets will use two different serializer depending on the current action.
`get_serializer_class` function will get a defined serializer if it exists or create a new one for the given model and use_case if not.

### For deep serialization of nested Model.
If you have a dict of list of ...., and you want to create it in one request, you can:

The posted request:
```JSON
{
  "title": "My Book",
  "description": "My first try to write something",
  "tags": [
    {
      "name": "action",
      "description": "battles!!!!!"
    },
    {
      "name": "adventure",
      "description": "Story driven"
    }
  ],
  "chapters": [
    {
      "number": 1,
      "content": "Chapter 1 ..."
    },
    {
      "number": 2,
      "content": "Chapter 2 ..."
    },
    {
      "number": 3,
      "content": "Chapter 3 ..."
    }
  ]
}
```

`views.py`
```Python
from rest_framework import status
from rest_framework.response import Response
from deepserializer import DeepViewSet

from myapp.models import Book, Chapter

class DeepCreateBookViewSets(DeepViewSet):
    queryset = Book.objects

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer()
        results = serializer.deep_update_or_create(
            self.queryset.model,
            [request.data],
            delete_models=[Chapter]
        )
        if any("ERROR" in item for item in results if isinstance(item, dict)):
            return Response(results, status=status.HTTP_409_CONFLICT)
        return Response(results, status=status.HTTP_201_CREATED)
```
The `deep_update_or_create` function get a list of data and return either a list of primary_keys or a list of representations
based on the optional parameter verbose.

The optional parameter are:
- `verbose` Define the amount of returned ny the function, by default it is `True`:
    - If `verbose=True` it will return a list of representations, in this case it will return almost the same as the `request.data` but with `id` and `book` inside the `chapters` dicts.
    - If `verbose=False` it will return a list of primary_keys, in this case it will return `["My Book"]`.
- `delete_models`: List of all the model to delete the previously linked instances not present in the `request.data`

If a validation error occurred during the creation process it will return the representations, regardless of `verbose`, with only the problematic fields + a new `ERROR` field, even for the models

The `update` or `create` in the `deep_update_or_create` function are based on the primary key of the dict:
- With primary key:  The function will search for this data in the database:
    - If the key exist: it will update this instance with the given data (the update will be with `partial=True`), but only one time. If other dict are found with this primary key for this model, the updating process will be skipped.
    - If the key does not exist: It will create a new instance of this model with the given data, but only one time. If other dict are found with this primary key for this model, the creation process will be skipped.
- Without primary key: The function will not search for this data in the database and will directly create it.

With this you can do things like this:
```JSON
[
  {
    "title": "My Book",
    "description": "My first try to write something",
    "tags": [
      {
        "name": "action",
        "description": "battles!!!!!"
      },
      "adventure"
    ],
    "chapters": [],
    "cover": {
      "id": -1,
      "url": "http://example.com/000000"
    },
  },
  {
    "title": "My Book 2",
    "description": "My second try to write something",
    "tags": [
      {
        "name": "action",
        "description": "battles!!!!!"
      }
    ],
    "chapters": [],
    "cover": {
      "id": -1,
      "url": "http://example.com/000000"
    },
  }
]
```
In the case that `action` and `-1` do not exist in the database:
The `action` Tag will be created only one time and will be linked to both `My Book` and `My Book 2`,
And the `-1` Image will be created one time with the new primary key `42` (for example) and be linked to both `My Book` and `My Book 2`.

### The types of relationships that are supported include:

- `one_to_one`: One instance of a model is related to one instance of another model.
- `one_to_many`: One instance of a model is related to many instances of another model.
- `many_to_one`: Many instances of a model are related to one instance of another model.
- `many_to_many`: Many instances of a model are related to many instances of another model.

And in reverse with:

- `related_name`: The name to use for the relation from the related object back to this one.

# Contributing

Contributions are welcome! Please read the contributing guidelines before getting started.

# License

This project is licensed under the terms of the MIT license.
