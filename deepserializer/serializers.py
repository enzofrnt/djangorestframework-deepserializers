"""
A unique serializer for all your need of deep read and deep write, made easy
"""

from collections import OrderedDict

from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.utils import model_meta
from rest_framework.utils.field_mapping import (get_nested_relation_kwargs, )


###################################################################################################
#
###################################################################################################


class DeepSerializer(serializers.ModelSerializer):
    """
    A unique serializer for all your need of deep read and deep write, made easy
    """
    _serializers = {}
    _mode = ""

    def __init_subclass__(cls, **kwargs):
        """
        Used to save the important information like:
        -> all the serializer inheriting this class
        -> all the nested models for this serializer
        -> all the prefetch_related for this serializer

        You can modify the cls.prefetch_related so that it only have certain fields
        the read_only_fields will be modified latter, but for the moment it works
        """
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "Meta"):
            model = cls.Meta.model
            cls._serializers[cls._mode + model.__name__] = cls
            cls._nested_models = cls.build_nested_models(model)
            cls._prefetch_related = [
                prefetch[2:]
                for prefetch in cls.build_prefetch_related(model, [model])
            ]
            cls.prefetch_related = cls.to_prefetch_related()
            cls.Meta.read_only_fields = tuple(
                model_meta.get_field_info(model).reverse_relations)

    @classmethod
    def build_nested_models(cls, model) -> dict:
        """
        Create a dict with the field name in key and the associated model in value.

        model: contain the model to get the nested model from
        """
        exclude_set = {
            field_name
            for field_name in model_meta.get_field_info(model).reverse_relations
            if field_name.endswith("_set")
        }
        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.related_model and f"{field_relation.name}_set" not in exclude_set
        }

    @classmethod
    def build_prefetch_related(cls, parent_model, exclude_models: list) -> list[str]:
        """
        Create the prefetch_related list,
        With all the prefetch from the nested model at maximum depth
        """
        prefetch_related = []
        for field_name, model in cls.build_nested_models(parent_model).items():
            if model not in exclude_models:
                current_prefetch = f"__{field_name}"
                prefetch_related.append(current_prefetch)
                for prefetch in cls.build_prefetch_related(model, exclude_models + [model]):
                    prefetch_related.append(current_prefetch + prefetch)
        return prefetch_related

    @classmethod
    def to_prefetch_related(cls, excludes: list[str] = []) -> list[str]:
        """
        Get the prefetch_related list for this class, two use case:
        -> queryset.prefetch_related(*self.to_prefetch_related())
        -> class.prefetch_related = class.to_prefetch_related(exclude=['model1', 'model2'])

        excludes: Field name of the model who will be removed from this serializer
        return: list of prefetch related filtered with the correct depth and without the excluded
        """
        return [
            prefetch_related
            for prefetch_related in cls._prefetch_related
            if len(prefetch_related.split('__')) < cls.Meta.depth + 2 and not any(
                prefetch_related.startswith(exclude)
                for exclude in excludes
                if exclude
            )
        ]

    @classmethod
    def get_nested_prefetch(cls, field_name: str) -> list[str]:
        """
        Used to get the prefetch_related of a nested serializer

        field_name: Field name of the model to get the prefetch from
        return: list of prefetch related starting with 'field_name'
        """
        nested_prefetch = []
        for prefetch in cls.prefetch_related:
            child_prefetch = prefetch.split('__')
            if 1 < len(child_prefetch) < cls.Meta.depth + 2 and child_prefetch[0] == field_name:
                nested_prefetch.append("__".join(child_prefetch[1:]))
        return nested_prefetch

    def get_default_field_names(self, declared_fields, model_info) -> list[str]:
        """
        Has been overriden to only display the fields with model inside prefetch_related
        """
        return (
                [model_info.pk.name] +
                list(declared_fields) +
                list(model_info.fields) +
                list(set(field.split('__')[0] for field in self.prefetch_related))
        )

    def build_nested_field(self, field_name: str, relation_info, nested_depth: int):
        """
        Has been overriden to enable the safe visualisation of a deeply nested models
        Without circular depth problem
        """
        serializer = self.get_serializer(
            relation_info.related_model,
            mode=f"Read{self.Meta.model.__name__}Nested"
        )
        serializer.prefetch_related = self.get_nested_prefetch(field_name)
        serializer.Meta.depth = nested_depth - 1
        return serializer, get_nested_relation_kwargs(relation_info)

    def deep_dict_travel(self, data: dict) -> tuple[str, dict]:
        """
        Recursively travel through a model to create the nested models first.
        Override it to change update_or_create into something else like get_or_create

        This algo only work with one_to_one, one_to_many or many_to_many relationships.
        If you need to create through a many_to_one, juste reverse your data

        data: The dict to create or update
        return: The primary key of the created instance and its data representation
        """
        nested = {}
        for field_name, model in self._nested_models.items():
            field_data = data.get(field_name, None)
            serializer = self.get_serializer(model, mode="Nested")(context=self.context)
            if isinstance(field_data, dict):
                data[field_name], nested[field_name] = serializer.deep_dict_travel(field_data)
            elif isinstance(field_data, list):
                if result := serializer.deep_list_travel(field_data):
                    data[field_name], nested[field_name] = map(list, result)
        return self.update_or_create(data, nested)

    def deep_list_travel(self, data_list: list[str | dict]) -> list[tuple[str, dict]]:
        """
        Recursively travel through a list of model to create the nested models first.
        Override it to change bulk_update_or_create into something else like bulk_get_or_create

        This algo only work with one_to_one, one_to_many or many_to_many relationships.
        If you need to create through a many_to_one, juste reverse your data

        data_list: A list of dict to create or update
        return: List of tuple of the created instance primary key and its data representation
        """
        data_and_nested_list = [(data, {}) for data in data_list]
        to_create = [
            data_and_nested
            for data_and_nested in data_and_nested_list
            if isinstance(data_and_nested[0], dict)
        ]
        for field_name, model in self._nested_models.items():
            serializer = self.get_serializer(model, mode="Nested")(context=self.context)
            if one_to_datas := [
                data_and_nested
                for data_and_nested in to_create
                if isinstance(data_and_nested[0].get(field_name, None), dict)
            ]:
                nested_results = serializer.deep_list_travel([
                    data[field_name]
                    for data, _ in one_to_datas
                ])
                for (data, nested), nested_result in zip(one_to_datas, nested_results):
                    data[field_name], nested[field_name] = nested_result
            elif many_to_datas := [
                data_and_nested
                for data_and_nested in to_create
                if isinstance(data_and_nested[0].get(field_name, None), list)
            ]:
                flatten_nested_results = serializer.deep_list_travel([
                    data
                    for data_sublist, _ in many_to_datas
                    for data in data_sublist[field_name]
                ])
                for data, nested in many_to_datas:
                    length = len(data[field_name])
                    if nested_result := flatten_nested_results[:length]:
                        data[field_name], nested[field_name] = map(list, zip(*nested_result))
                        flatten_nested_results = flatten_nested_results[length:]
        return self.bulk_update_or_create(data_and_nested_list)

    def update_or_create(self, data: dict, nested: dict, instances: dict = None
                         ) -> tuple[str, dict]:
        """
        Create or update one instance with data, base on the model primary key

        data: the dict that contain the data who will be created or updated
        nested: The nested model representations to update the data representation with
        instances: Contain all possible instances for the data to update
        -> if instances is None, will make db request to get back the instance if it exists

        return: tuple of:
        -> primary_key or 'Failed to serialize' for the created or updated model
        -> representation or ERROR information for the created or updated model
        """
        if pk := data.get(self.Meta.model._meta.pk.name, None):
            if instances is not None:
                self.instance = instances.get(pk, None)
            else:
                self.instance = self.Meta.model.objects.filter(pk=pk).first()
        self.initial_data, self.partial = data, bool(self.instance)
        if self.is_valid():
            return self.save().pk, OrderedDict(self.data, **nested)
        return (f"Failed to serialize {self.Meta.model.__name__}",
                OrderedDict(nested, ERROR=self.errors))

    def bulk_update_or_create(self, data_and_nested: list[tuple[any, dict]]) -> list[tuple]:
        """
        Create or update multiple instance with the data in data_and_nested.
        The instances are updated or created one time base on the model primary key.
        If the primary_key exist, it will update the instance one time and reuse
        this instance result when the primary key is found inside data_and_nested again
        If the primary_key does not exist, it will create a new instance and reuse
        this instance result when the primary key is found inside data_and_nested again
        If there is no primary_key, it will create a new instance without reusing other

        data_and_nested: list containing tuple of:
        -> data (dict that contain the data who will be created or updated)
        -> nested (nested model representations to update the data representation with)

        return: list containing tuple of:
        -> primary_key or 'Failed to serialize' for the created or updated model
        -> representation or ERROR information for the created or updated model
        """
        pks_and_representations, created = [], {}
        model = self.Meta.model
        pk_name = model._meta.pk.name
        found_pks = set(data[pk_name] for data, _ in data_and_nested if pk_name in data)
        instances = model.objects.prefetch_related(*self.to_prefetch_related()
                                                   ).in_bulk(found_pks)
        for data, nested in data_and_nested:
            if isinstance(data, dict):
                found_pk = data.get(pk_name, None)
                if found_pk not in created:
                    created_pk, representation = self.update_or_create(
                        data, nested, instances=instances)
                    found_pk = found_pk if found_pk is not None else created_pk
                    created[found_pk] = (created_pk, representation)
                    self.instance = None
                    if "ERROR" not in representation:
                        del self._data, self._validated_data
                pks_and_representations.append(created[found_pk])
            else:
                pks_and_representations.append((data, data))
        return pks_and_representations

    def deep_create(self, data: dict | list, verbose: bool = True) -> list[str] | list[dict]:
        """
        Create either a list of model or a unique model with their nested models at any depth.

        It is recommended to construct the json that will be created after receiving the data
        and not use the pure request data, but you do you ¯\\_(ツ)_//¯

        If the resulting data is too big to be sent back,
        'verbose'=False is used to only send the primary_key of the created model.
        If there has been errors it will send the dict with the errors regardless of verbose

        The deep_create only work with one_to_one, one_to_many or many_to_many relationships,
            If you need to create a model through a many_to_one juste reverse it like:
            example of 'Admin' group: {
                "id": "Admin",
                "description": "Group of admin"
                "users": [
                    {
                        "firstname": 'john',
                        "lastname": 'Doe'
                    },
                    {
                        "firstname": 'jane',
                        "lastname": 'Doe'
                    }
                ]
            }
            changed into: [
                {
                    "firstname": 'john',
                    "lastname": 'Doe'
                    "group": {
                        "id": "Admin"
                        "description": "Group of admin"
                    }
                },
                {
                    "firstname": 'Jane',
                    "lastname": 'Doe'
                    "group": {
                        "id": "Admin"
                        "description": "Group of admin"
                    }
                }
            ]
        """
        try:
            with atomic():
                serializer = self.get_serializer(self.Meta.model,
                                                 mode="Nested")(context=self.context)
                if data and isinstance(data, dict):
                    primary_key, representation = serializer.deep_dict_travel(data)
                    if "ERROR" in representation:
                        raise ValidationError(representation)
                    return representation if verbose else primary_key
                elif data and isinstance(data, list):
                    primary_key, representation = map(list,
                                                      zip(*serializer.deep_list_travel(data)))
                    if errors := [d for d in representation if "ERROR" in d]:
                        raise ValidationError(errors)
                    return representation if verbose else primary_key
        except ValidationError as e:
            return e.detail

    @classmethod
    def get_serializer(cls, _model, mode: str = ""):
        """
        Get back or create a serializer for the _model and its mode.
        Manually created serializer inheriting DeepViewSet will automatically be used for its mode

        If your serializer is only used in a specific use-case, write it in the mode

        _model: Contain the model related to the serializer wanted
        mode: Contain the use that this serializer will be used for,
        -> if empty, it will be the main serializer for this model
        """
        if mode + _model.__name__ not in cls._serializers:
            parent = cls.get_serializer(_model) if mode else DeepSerializer

            class CommonSerializer(parent):
                """
                Common serializer template.
                Inherit either the DeepSerializer or the main model serializer.
                """
                _mode = mode

                class Meta:
                    model = _model
                    depth = 0
                    fields = parent.Meta.fields if mode else '__all__'

        return cls._serializers[mode + _model.__name__]


###################################################################################################
#
###################################################################################################
