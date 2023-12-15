"""
This module is used to create a serializer that can be used to create or update a model
with its nested models at any depth.
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
            -> all the serializer inheriting DeepSerializer and avoid creating already created
            serializer
            -> all the nested_models for the current serializer
            -> all the prefetch_related for the current serializer

        You can modify the cls.prefetch_related so that it only have certain fields
        the read_only_fields will be modified latter, but for the moment it works
        """
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "Meta"):
            model = cls.Meta.model
            cls._serializers[cls._mode + model.__name__] = cls
            cls._nested_models = cls.build_nested_models(model)
            cls._prefetch_related = [p[2:] for p in cls.build_prefetch_related(model, [model])]
            cls.prefetch_related = cls.to_prefetch_related()
            cls.Meta.read_only_fields = tuple(model_meta.get_field_info(model).reverse_relations)

    @classmethod
    def build_nested_models(cls, model):
        """
        Used to build the dict with all the fields with their nested model for this model

        model: contain the model to get the nested model from
        """
        exclude_set = {
            name
            for name in model_meta.get_field_info(model).reverse_relations
            if name.endswith("_set")
        }

        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.related_model and f"{field_relation.name}_set" not in exclude_set
        }

    @classmethod
    def build_prefetch_related(cls, parent_model, exclude_models):
        """
        Used to build the prefetch_related with all the nested model at maximum depth

        Used inside __init_subclass__ and should never be used alone,
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
    def to_prefetch_related(cls, excludes: list[str] = []):
        """
        Used to get the prefetch_related from the current serializer,
            for either: -> queryset.prefetch_related(*self.to_prefetch_related())
                        -> class.prefetch_related = class.to_prefetch_related(
                                                        exclude=['field_model1', 'field_model2']
                                                    )

        field_name: contain the field name of the model who will be displayed with a serializer
        return: list of prefetch related filtered by depth and exclude
        """
        if excludes is None:
            excludes = []
        return [
            prefetch_related
            for prefetch_related in cls._prefetch_related
            if len(prefetch_related.split('__')) < cls.Meta.depth + 2
               and not any(prefetch_related.startswith(exclude) for exclude in excludes if exclude)
        ]

    @classmethod
    def get_nested_prefetch(cls, field_name):
        """
        Used to get the prefetch_related of a nested serializer

        field_name: contain the field name of the model who will be displayed with a serializer
        return: list of prefetch related starting with 'field_name'
        """
        nested_prefetch = []
        for prefetch in cls.prefetch_related:
            child_prefetch = prefetch.split('__')
            if 1 < len(child_prefetch) < cls.Meta.depth + 2 and child_prefetch[0] == field_name:
                nested_prefetch.append("__".join(child_prefetch[1:]))
        return nested_prefetch

    def get_default_field_names(self, declared_fields, model_info):
        """
        Has been overriden to only display requested fields with only the nested models
        inside prefetch_related
        """
        return (
                [model_info.pk.name] +
                list(declared_fields) +
                list(model_info.fields) +
                list(set(field.split('__')[0] for field in self.prefetch_related))
        )

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """
        Has been overriden to enable the safe visualisation of
         a deeply nested models without circular problem
        """
        serializer = self.get_serializer(
            relation_info.related_model,
            mode=f"Read{self.Meta.model.__name__}Nested"
        )
        serializer.prefetch_related = self.get_nested_prefetch(field_name)
        serializer.Meta.depth = nested_depth - 1
        return serializer, get_nested_relation_kwargs(relation_info)

    def deep_dict_travel(self, data: dict) -> tuple:
        """
        Used to travel inside a model and create the nested model first,
            Will recursively create the upper instance to put the primary key of
             the nested object inside the fields

        Used inside deep_create and should never be called alone,
            but you can override it if you want to change it like ->
             -> Change bulk_update_or_create into something else like bulk_get_or_create
        data: contain the dict to create or update
        return: the result of update_or_create
        """
        nested = {}
        for field_name, model in self._nested_models.items():
            # travel through all nested models
            field_data = data.get(field_name, None)
            serializer = self.get_serializer(model, mode="Nested")(context=self.context)
            if isinstance(field_data, dict):
                # Executed for one_to_one or one_to_many relationships
                data[field_name], nested[field_name] = serializer.deep_dict_travel(field_data)
            elif isinstance(field_data, list):
                # Executed for many_to_many relationships
                data[field_name], nested[field_name] = map(
                    list,
                    zip(*serializer.deep_list_travel(field_data))
                )
        return self.update_or_create(data, nested)

    def deep_list_travel(self, data_list: list) -> list[tuple]:
        """
        Used to travel inside a list of models and create the nested model first,
            Will recursively create the upper instance to put the primary key of
            the nested object inside the fields

        Used inside deep_create and should never be called alone,
            but you can override it if you want to change it like ->
             -> Change bulk_update_or_create into something else like bulk_get_or_create

        data_list: contain the list of dict to create or update
        return: the result of bulk_update_or_create
        """
        data_and_nested_list = [
            (data, {}) for data in data_list
        ]

        to_create = [
            d_n for d_n in data_and_nested_list
            if isinstance(d_n[0], dict)
        ]

        for field_name, model in self._nested_models.items():
            # travel through all nested models
            serializer = self.get_serializer(
                model, mode="Nested"
            )(context=self.context)

            if dicts := [
                d_n for d_n in to_create
                if isinstance(d_n[0].get(field_name, None), dict)
            ]:
                # Executed for one_to_one or one_to_many relationships
                dicts_data = [d[field_name] for d, _ in dicts]
                zip_dicts = zip(dicts, serializer.deep_list_travel(dicts_data))

                for (data, rep), result in zip_dicts:
                    data[field_name], rep[field_name] = result

            elif lists := [
                d_n for d_n in to_create
                if isinstance(d_n[0].get(field_name, None), list)
            ]:
                # Executed for many_to_many relationships
                lists_data = [i for d, _ in lists for i in d[field_name]]
                flatten_results = serializer.deep_list_travel(lists_data)

                for data, nested in lists:
                    if length := len(data[field_name]):
                        data_zip = zip(*flatten_results[:length])
                        data[field_name], nested[field_name] = map(list, data_zip)
                        flatten_results = flatten_results[length:]

        return self.bulk_update_or_create(data_and_nested_list)

    def update_or_create(self, data: dict, nested: dict, instances: dict = None):
        """
        Create one instance with data without loosing functionality of Django or DRF

        Is only used for deep_create but can be used for anything else with a little bit of
        imagination
        instances: Used for performance,
            if you already looked for all instance somewhere you can give them to instances
            and save one db request

        data: dict that will be created or updated
        nested: dict that contain the nested model representations
        return: tuple of -> primary_key of the model if there has been no errors,
                                else it returns 'Failed to serialize'
                         -> representation of the models with their nested model if no errors,
                                else it returns the dict with a 'ERROR' field that
                                contain what happened
        """
        model = self.Meta.model
        if pk := data.get(model._meta.pk.name, None):
            if instances is not None:
                self.instance = instances.get(pk, None)
            else:
                self.instance = model.objects.filter(pk=pk).first()
        self.initial_data, self.partial = data, bool(self.instance)
        if self.is_valid():
            return self.save().pk, OrderedDict(self.data, **nested)
        return f"Failed to serialize {model.__name__}", OrderedDict(nested, ERROR=self.errors)

    def bulk_update_or_create(self, data_and_nested: list[tuple[dict, dict]]) -> list[tuple]:
        """
        Create all the instances in data in a bulk like manner without loosing
        functionality of Django or DRF

        Is only used for deep_create but can be used for anything else with a
        little bit of imagination

        data_and_nested: list containing tuple of 
                                    -> data (dict that will be created or updated)
                                    -> nested (dict that contain the nested model representations)
        return: list containing tuple of 
                                    -> primary_key (pk of the created instances)
                                    -> representation (representation of the created instances)
        """
        pks_and_representations, created = [], {}
        pk_name = self.Meta.model._meta.pk.name
        found_pks = set(d[pk_name] for d, _ in data_and_nested if pk_name in d)
        instances = self.Meta.model.objects.prefetch_related(
                        *self.to_prefetch_related()
                    ).in_bulk(found_pks)
        for data, nested in data_and_nested:
            if isinstance(data, dict):
                found_pk = data.get(pk_name, None)
                if found_pk not in created:
                    created_pk, representation = self.update_or_create(
                                                                        data,
                                                                        nested,
                                                                        instances=instances
                                                                    )
                    found_pk = found_pk if found_pk is not None else created_pk
                    created[found_pk] = (created_pk, representation)
                    self.instance = None
                    if "ERROR" not in representation:
                        del self._data, self._validated_data
                pks_and_representations.append(created[found_pk])
            else:
                pks_and_representations.append((data, data))
        return pks_and_representations

    def deep_create(self, data: dict | list, verbose: bool = True):
        """
        Create either a list of model or a unique model with their nested models at any depth.

        For security reason, it is recommended to construct the json that 
        will be created in the back,
            but you do you ¯\\_(ツ)_//¯

        If the resulting data is too big to be sent back,
            'verbose'=False is used to only send the primary_key of the created model,
            if there has been errors it will only send the dict with the errors regardless
            of verbose

        The deep_create only work with one_to_one, one_to_many or many_to_many relationships,
            If you need to create a model through a many_to_one juste reverse your json
            to get a one_to_many
            example of 'Admin' group: {
                "id": "Admin",
                "description": "Group of admin"
                "users": [
                    {
                        "firstname": 'john',
                        "lastname": 'Doe',
                        "group": "Admin"
                    },
                    {
                        "firstname": 'jane',
                        "lastname": 'Doe',
                        "group": "Admin"
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
            If the id of this group does not exist it will be used so that only 
            one group 'Admin' is created, this group admin will then be reused for users needing it.
            If the id exist it will be updated one time and used for any users needing it.
        """
        try:
            with atomic():
                serializer_class = self.get_serializer(self.Meta.model, mode="Nested")
                serializer = serializer_class(context=self.context)
                if data and isinstance(data, dict):
                    primary_key, representation = serializer.deep_dict_travel(data)
                    if "ERROR" in representation:
                        raise ValidationError(representation)
                elif data and isinstance(data, list):
                    primary_key, representation = map(list, zip(*serializer.deep_list_travel(data)))
                    if errors := [d for d in representation if "ERROR" in d]:
                        raise ValidationError(errors)
                else:
                    return None
            return representation if verbose else primary_key
        except ValidationError as e:
            return e.detail

    @classmethod
    def get_serializer(cls, _model, mode: str = ""):
        """
        Create a serializer for the _model and its mode if it does not exist,
        else it gets the serializer back
        You can create your own serializer that inherit DeepSerializer,
        and it will be used when called upon
        If your serializer is only used in a specific use-case, write it in the mode

        _model: Contain the model related to the serializer wanted
        mode: Contain the use that this serializer will be used for,
            if empty, it will be the main serializer for this model
        """
        if mode + _model.__name__ not in cls._serializers:
            parent = cls.get_serializer(_model) if mode else DeepSerializer

            class CommonSerializer(parent):
                _mode = mode

                class Meta:
                    model = _model
                    depth = 0
                    fields = parent.Meta.fields if mode else '__all__'

        return cls._serializers[mode + _model.__name__]


###################################################################################################
#
###################################################################################################
