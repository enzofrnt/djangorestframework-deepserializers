"""
A unique serializer for all your need of deep read and deep write, made easy
"""
from collections import OrderedDict

from django.db.models import Model
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

    def __init_subclass__(cls, **kwargs):
        """
        Used to save the important information like:
        -> all the serializer inheriting DeepSerializer
        -> all the types of relationships for this serializer
        -> all the prefetch_related for this serializer

        You can modify the cls.prefetch_related so that it only have certain fields
        the read_only_fields will be modified latter, but for the moment it works
        """
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "Meta"):
            model = cls.Meta.model
            if not hasattr(cls.Meta, "mode"):
                cls.Meta.mode = ""
            if not hasattr(cls.Meta, "read_only_fields"):
                cls.Meta.read_only_fields = tuple()
            cls._serializers[cls.Meta.mode + model.__name__] = cls
            cls._many_to_many = cls.build_many_to_many_models(model)
            cls._one_to_many = cls.build_one_to_many_models(model)
            cls._any_to_one = dict(cls.build_one_to_one_models(model),
                                   **cls.build_many_to_one_models(model))
            cls._relationships = cls.build_relationship_models(model)
            cls._prefetch_related = cls.build_prefetch_related(model)
            cls.prefetch_related = cls.get_prefetch_related()
            cls.Meta.read_only_fields += tuple(
                model_meta.get_field_info(model).reverse_relations)

    @classmethod
    def build_one_to_one_models(cls, model: Model) -> dict[str, Model]:
        """
        Get all the one_to_one relationships models for a given model.
        With the field name in key and the Model in Value
        """
        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.one_to_one
        }

    @classmethod
    def build_one_to_many_models(cls, model: Model) -> dict[str, tuple[Model, str]]:
        """
        Get tuple of all the one_to_many relationships.
        Get all the one_to_many relationships models for a given model.
        With the field name in key and a tuple in Value with:
        -> models
        -> field name of the related_model for a given model
        (the reverse of related_name)
        """
        return {
            field_relation.name: (
                field_relation.related_model,
                field_relation.field.name
            )
            for field_relation in model._meta.get_fields()
            if field_relation.one_to_many
               and field_relation.related_name
        }

    @classmethod
    def build_many_to_one_models(cls, model: Model) -> dict[str, Model]:
        """
        Get all the many_to_one relationships models for a given model.
        With the field name in key and the Model in Value
        """
        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.many_to_one
        }

    @classmethod
    def build_many_to_many_models(cls, model: Model) -> dict[str, Model]:
        """
        Get all the many_to_many relationships models for a given model.
        With the field name in key and the Model in Value
        """
        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.many_to_many
        }

    @classmethod
    def build_relationship_models(cls, model: Model) -> dict[str, Model]:
        """
        Get all the relationships models for a given model.
        With the field name in key and the Model in Value
        """
        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.related_model
               and (not field_relation.one_to_many
                    or field_relation.related_name)
        }

    @classmethod
    def build_prefetch_related(cls, parent_model: Model) -> list[str]:
        """
        Create the prefetch_related list,
        With all the prefetch from the nested model at maximum depth
        """

        def _build(_model, _excludes):
            prefetch_related = []
            for field_name, model in cls.build_relationship_models(_model).items():
                if model not in _excludes:
                    current_prefetch = f"__{field_name}"
                    prefetch_related.append(current_prefetch)
                    for prefetch in _build(model, _excludes + [model]):
                        prefetch_related.append(current_prefetch + prefetch)
            return prefetch_related

        return [
            prefetch[2:]
            for prefetch in _build(parent_model, [parent_model])
        ]

    @classmethod
    def get_prefetch_related(cls, excludes: list[str] = []) -> list[str]:
        """
        Get the prefetch_related list for this class, two use case:
        -> queryset.prefetch_related(*self.to_prefetch_related())
        -> class.prefetch_related = class.to_prefetch_related(exclude=['Model1', 'Model2'])

        excludes: Field name of the model who will be removed from this serializer
        return: list of prefetch related filtered with the correct depth and without the excluded
        """
        return [
            prefetch_related
            for prefetch_related in cls._prefetch_related
            if len(prefetch_related.split('__')) < cls.Meta.depth + 2
            and not any(
                prefetch_related.startswith(exclude)
                for exclude in excludes
                if exclude
            )
        ]

    @classmethod
    def get_nested_prefetch_related(cls, field_name: str) -> list[str]:
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

    def build_nested_field(self, field_name: str, relation_info, nested_depth: int) -> tuple:
        """
        Has been overriden to enable the safe visualisation of a deeply nested models
        Without circular depth problem
        """
        serializer = self.get_serializer(
            relation_info.related_model,
            mode=f"Read{self.Meta.model.__name__}Nested"
        )
        serializer.prefetch_related = self.get_nested_prefetch_related(field_name)
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
        for field_name, model in self._any_to_one.items():
            if isinstance(field_data := data.get(field_name, None), dict):
                serializer = self.get_serializer(model, mode="Nested")(context=self.context)
                data[field_name], nested[field_name] = serializer.deep_dict_travel(field_data)
        for field_name, model in self._many_to_many.items():
            if isinstance(field_data := data.get(field_name, None), list):
                serializer = self.get_serializer(model, mode="Nested")(context=self.context)
                if result := serializer.deep_travels(field_data):
                    data[field_name], nested[field_name] = map(list, zip(*result))
        create_later = {
            field_name: (model, reverse_name, data.pop(field_name))
            for field_name, (model, reverse_name) in self._one_to_many.items()
            if isinstance(data.get(field_name, None), list)
        }
        pk, representation = self.update_or_create(data, nested)
        for field_name, (model, reverse_name, field_data) in create_later.items():
            for dict_data in field_data:
                if isinstance(dict_data, dict):
                    dict_data[reverse_name] = pk
            serializer = self.get_serializer(model, mode="Nested")(context=self.context)
            if result := serializer.deep_travels(field_data):
                _, representation[field_name] = map(list, zip(*result))
        return pk, representation

    def deep_travels(self, datas: list[any]) -> list[tuple[str, dict]]:
        """
        Recursively travel through a list of model to create the nested models first.
        Override it to change bulk_update_or_create into something else like bulk_get_or_create

        data_list: A list of dict to create or update
        return: List of tuple of the created instance primary key and its data representation
        """
        all_data_and_nested = [(data, {}) for data in datas]

        for field_name, model in self._any_to_one.items():
            filtered_data_and_nested, field_datas = [], []
            for data, nested in all_data_and_nested:
                if isinstance(data, dict):
                    field_data = data.get(field_name, None)
                    if isinstance(field_data, dict):
                        filtered_data_and_nested.append((data, nested))
                        field_datas.append(field_data)
            if filtered_data_and_nested:
                serializer = self.get_serializer(model, mode="Nested")(context=self.context)
                results = serializer.deep_travels(field_datas)
                for (data, nested), result in zip(filtered_data_and_nested, results):
                    data[field_name], nested[field_name] = result

        for field_name, model in self._many_to_many.items():
            filtered_data_and_nested, field_datas = [], []
            for data, nested in all_data_and_nested:
                if isinstance(data, dict):
                    field_data = data.get(field_name, None)
                    if isinstance(field_data, list) and (length := len(field_data)) > 0:
                        filtered_data_and_nested.append((data, nested, length))
                        field_datas += field_data
            if filtered_data_and_nested:
                serializer = self.get_serializer(model, mode="Nested")(context=self.context)
                results = serializer.deep_travels(field_datas)
                for data, nested, length in filtered_data_and_nested:
                    data[field_name], nested[field_name] = map(list, zip(*results[:length]))
                    results = results[length:]

        create_later = {}
        for field_name, (model, reverse_name) in self._one_to_many.items():
            filtered_info = []
            for index, (data, _) in enumerate(all_data_and_nested):
                if isinstance(data, dict):
                    field_data = data.pop(field_name, None)
                    if isinstance(field_data, list) and (length := len(field_data)) > 0:
                        filtered_info.append((index, length, field_data))
            if filtered_info:
                create_later[field_name] = (model, reverse_name, filtered_info)

        pk_and_representation = self.bulk_update_or_create(all_data_and_nested)

        for field_name, (model, reverse_name, filtered_info) in create_later.items():
            field_datas = []
            for index, _, field_data in filtered_info:
                for data in field_data:
                    data[reverse_name] = pk_and_representation[index][0]
                    field_datas.append(data)
            serializer = self.get_serializer(model, mode="Nested")(context=self.context)
            results = serializer.deep_travels(field_datas)
            for index, length, _ in filtered_info:
                _, pk_and_representation[index][1][field_name] = map(list, zip(*results[:length]))
                results = results[length:]

        return pk_and_representation

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

    def bulk_update_or_create(self, data_and_nested: list[tuple[any, dict]]
                              ) -> list[tuple[str, dict]]:
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
        instances = model.objects.prefetch_related(*self.get_prefetch_related()
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

    def deep_create(self, data: dict | list, verbose: bool = True, model: any = None
                    ) -> list[str] | list[dict]:
        """
        Create either a list of model or a unique model with their nested models at any depth.

        It is recommended to construct the json that will be created after receiving the data
        and not use the pure request data, but you do you ¯\\_(ツ)_//¯

        If the resulting data is too big to be sent back,
        'verbose'=False is used to only send the primary_key of the created model.
        If there has been errors it will send the dict with the errors regardless of verbose

        The deep_create work with:
        one_to_one, one_to_many, many_to_one and many_to_many relationships.
        """
        try:
            with atomic():
                serializer = self.get_serializer(
                    model if model else self.Meta.model,
                    mode="Nested"
                )(context=self.context)
                if data and isinstance(data, dict):
                    primary_key, representation = serializer.deep_dict_travel(data)
                    if "ERROR" in representation:
                        raise ValidationError(representation)
                    return representation if verbose else primary_key
                elif data and isinstance(data, list):
                    primary_key, representation = map(list,
                                                      zip(*serializer.deep_travels(data)))
                    if errors := [d for d in representation if "ERROR" in d]:
                        raise ValidationError(errors)
                    return representation if verbose else primary_key
        except ValidationError as e:
            return e.detail

    @classmethod
    def get_serializer(cls, model: Model, mode: str = ""):
        """
        Get back or create a serializer for the _model and its mode.
        Manually created serializer inheriting DeepViewSet will automatically be used for its mode

        If your serializer is only used in a specific use-case, write it in the mode

        _model: Contain the model related to the serializer wanted
        mode: Contain the use that this serializer will be used for,
        -> if empty, it will be the main serializer for this model
        """
        if mode + model.__name__ not in cls._serializers:
            parent = cls.get_serializer(model) if mode else DeepSerializer
            _mode, _model = mode, model

            class CommonSerializer(parent):
                """
                Common serializer template.
                Inherit either the DeepSerializer or the main model serializer.
                """

                class Meta:
                    model = _model
                    depth = 0
                    fields = parent.Meta.fields if _mode else '__all__'
                    mode = _mode

        return cls._serializers[mode + model.__name__]

###################################################################################################
#
###################################################################################################
