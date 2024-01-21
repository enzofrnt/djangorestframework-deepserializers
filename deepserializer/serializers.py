"""
A unique serializer for all your need of deep read and deep write, made easy
"""
from collections import OrderedDict

from django.db.models import Model
from django.db.transaction import atomic
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.utils.field_mapping import (get_nested_relation_kwargs, )


###################################################################################################
#
###################################################################################################


class DeepSerializer(serializers.ModelSerializer):
    """
    A unique serializer for all your need of deep read and deep write, made easy
    """
    _serializers = {}
    _pk_error = "Failed to Serialize"

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
            if not hasattr(cls.Meta, "use_case"):
                cls.Meta.use_case = ""
            model = cls.Meta.model
            excludes = [] if cls.Meta.fields == '__all__' else [
                related_model
                for field_name, related_model in cls.get_all_relationships(model, []).items()
                if field_name not in cls.Meta.fields
            ]
            cls._serializers[cls.Meta.use_case + model.__name__] = cls
            cls._prefetch_related = cls.build_prefetch_related(model, excludes)
            cls._all_relationships = cls.get_all_relationships(model, excludes)
            cls._forward_relationships = cls.get_forward_relations(model, excludes)
            cls._reverse_relationships = cls.get_reverse_relations(model, excludes)
            cls.Meta.read_only_fields = tuple({
                *cls._reverse_relationships["one"],
                *cls._reverse_relationships["many"],
                *(cls.Meta.read_only_fields if hasattr(cls.Meta, "read_only_fields") else [])
            })
            cls.prefetch_related = cls.get_prefetch_related(depth=cls.Meta.depth)

    def __init__(self, *args, **kwargs):
        if (depth := kwargs.pop("depth", None)) is not None:
            self.Meta.depth = depth
        if (prefetch_related := kwargs.pop("prefetch_related", None)) is not None:
            self.prefetch_related = prefetch_related
        super().__init__(*args, **kwargs)

    @classmethod
    def get_all_relationships(cls, model: Model, excludes: list[Model]) -> dict[str, Model]:
        """
        Get all the relationships models for a given model.
        With the field name in key and the Model in Value
        """
        return {
            field_relation.name: field_relation.related_model
            for field_relation in model._meta.get_fields()
            if field_relation.related_model
            and (not hasattr(field_relation, "field") or field_relation.related_name)
            and field_relation.related_model not in excludes
        }

    @classmethod
    def get_forward_relations(cls, model: Model, excludes: list[Model]) -> dict[str, dict[str, Model]]:
        return {
            "many": {
                field_relation.name: field_relation.related_model
                for field_relation in model._meta.get_fields()
                if (field_relation.many_to_many or field_relation.one_to_many)
                and not hasattr(field_relation, "field")
                and field_relation.related_model not in excludes
            },
            "one": {
                field_relation.name: field_relation.related_model
                for field_relation in model._meta.get_fields()
                if (field_relation.one_to_one or field_relation.many_to_one)
                and not hasattr(field_relation, "field")
                and field_relation.related_model not in excludes
            }
        }

    @classmethod
    def get_reverse_relations(cls, model: Model, excludes: list[Model]) -> dict[str, dict[str, tuple[Model, str]]]:
        return {
            "many": {
                field_relation.name: (field_relation.related_model, field_relation.field.name)
                for field_relation in model._meta.get_fields()
                if (field_relation.many_to_many or field_relation.one_to_many)
                and hasattr(field_relation, "field")
                and field_relation.related_name
                and field_relation.related_model not in excludes
            },
            "one": {
                field_relation.name: (field_relation.related_model, field_relation.field.name)
                for field_relation in model._meta.get_fields()
                if (field_relation.one_to_one or field_relation.many_to_one)
                and hasattr(field_relation, "field")
                and field_relation.related_name
                and field_relation.related_model not in excludes
            }
        }

    @classmethod
    def build_prefetch_related(cls, parent_model: Model, excludes: list[Model]) -> list[str]:
        """
        Create the prefetch_related list,
        With all the prefetch from the nested model at maximum depth
        """
        prefetch_related = []
        for field_name, model in cls.get_all_relationships(parent_model, excludes).items():
            prefetch_related.append(field_name)
            for prefetch in cls.build_prefetch_related(model, excludes + [parent_model]):
                prefetch_related.append(f"{field_name}__{prefetch}")
        return prefetch_related

    @classmethod
    def get_prefetch_related(cls, excludes: list[str] = [], depth: int = 0) -> list[str]:
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
            if len(prefetch_related.split('__')) < depth + 2
            and not any(
                prefetch_related.startswith(exclude)
                for exclude in excludes
                if exclude
            )
        ]

    def get_nested_prefetch_related(self, field_name: str) -> list[str]:
        """
        Used to get the prefetch_related of a nested serializer

        field_name: Field name of the model to get the prefetch from
        return: list of prefetch related starting with 'field_name'
        """
        nested_prefetch = []
        for prefetch in self.prefetch_related:
            child_prefetch = prefetch.split('__')
            if 1 < len(child_prefetch) < self.Meta.depth + 2 and child_prefetch[0] == field_name:
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
                list(field for field in self.prefetch_related if '__' not in field)
        )

    def build_nested_field(self, field_name: str, relation_info, nested_depth: int) -> tuple:
        """
        Has been overriden to enable the safe visualisation of a deeply nested models
        Without circular depth problem
        """
        serializer = self.get_serializer_class(relation_info.related_model, use_case=f"Deep")
        nested_relation_kwargs = get_nested_relation_kwargs(relation_info)
        nested_relation_kwargs["depth"] = nested_depth - 1
        nested_relation_kwargs["prefetch_related"] = self.get_nested_prefetch_related(field_name)
        return serializer, nested_relation_kwargs

    def _process_forward_relations(self, datas_and_nesteds: list[tuple], delete_models: list[Model]):

        for field_name, model in self._forward_relationships["one"].items():
            filtered_datas_info, field_datas = [], []
            for data, nested in datas_and_nesteds:
                if isinstance(data, dict) and isinstance(field_data := data.get(field_name, None), dict):
                    filtered_datas_info.append((data, nested))
                    field_datas.append(field_data)
            if filtered_datas_info:
                serializer = self.get_serializer_class(model, use_case="Deep")(context=self.context)
                for (data, nested), result in zip(filtered_datas_info, serializer.deep_process(field_datas, delete_models)):
                    data[field_name], nested[field_name] = result

        for field_name, model in self._forward_relationships["many"].items():
            filtered_datas_info, field_datas = [], []
            for data, nested in datas_and_nesteds:
                if isinstance(data, dict) and isinstance(field_data := data.get(field_name, None), list):
                    if (length := len(field_data)) > 0:
                        filtered_datas_info.append((data, nested, length))
                        field_datas += field_data
            if filtered_datas_info:
                serializer = self.get_serializer_class(model, use_case="Deep")(context=self.context)
                results = serializer.deep_process(field_datas, delete_models)
                for data, nested, length in filtered_datas_info:
                    data[field_name], nested[field_name] = map(list, zip(*results[:length]))
                    results = results[length:]

    def _process_reverse_relations(self, datas: list, primary_keys: list, representations: list, delete_models: list[Model]):

        for field_name, (model, reverse_name) in self._reverse_relationships["one"].items():
            filtered_datas_info, field_datas = [], []
            for index, data in enumerate(datas):
                if isinstance(data, dict) and isinstance(field_data := data.get(field_name, None), dict):
                    field_data[reverse_name] = primary_keys[index]
                    filtered_datas_info.append(index)
                    field_datas.append(field_data)
            if filtered_datas_info:
                serializer = self.get_serializer_class(model, use_case="Deep")(context=self.context)
                for index, result in zip(filtered_datas_info, serializer.deep_process(field_datas, delete_models)):
                    _, representations[index][field_name] = result

        for field_name, (model, reverse_name) in self._reverse_relationships["many"].items():
            filtered_datas_info, field_datas = [], []
            for index, data in enumerate(datas):
                if isinstance(data, dict) and isinstance(field_data := data.get(field_name, None), list):
                    if (length := len(field_data)) > 0:
                        for item in field_data:
                            if isinstance(item, dict):
                                item[reverse_name] = primary_keys[index]
                        filtered_datas_info.append((index, length))
                        field_datas += field_data
            if filtered_datas_info:
                serializer = self.get_serializer_class(model, use_case="Deep")(context=self.context)
                results = serializer.deep_process(field_datas, delete_models)
                for index, length in filtered_datas_info:
                    _, representations[index][field_name] = map(list, zip(*results[:length]))
                    results = results[length:]

    def _clean_datas_representation(self, representations: list, delete_models: list[Model]):
        to_deletes: dict[str, tuple[Model, set]] = {}
        for representation in representations:
            if isinstance(representation, dict):
                if "ERROR" not in representation and any(
                    (isinstance(field, list) and any(f"ERROR" in item for item in field if isinstance(item, dict)))
                    or (isinstance(field, dict) and "ERROR" in field)
                    for field in representation.values()
                ):
                    representation["ERROR"] = "Failed to Serialize nested objects"
                old_nested = representation.pop("OLD_NESTED", {})
                for field_name, model in self._all_relationships.items():
                    if model in delete_models:
                        field_datas = old_nested.get(field_name, [])
                        old_primary_keys = set(
                            primary_key[model._meta.pk.name] if isinstance(primary_key, dict) else primary_key
                            for primary_key in (field_datas if isinstance(field_datas, list) else [field_datas])
                            if primary_key
                        )
                        field_datas = representation.get(field_name, [])
                        new_primary_keys = set(
                            primary_key[model._meta.pk.name] if isinstance(primary_key, dict) else primary_key
                            for primary_key in (field_datas if isinstance(field_datas, list) else [field_datas])
                            if primary_key
                        )
                        if unused_primary_keys := old_primary_keys.difference(new_primary_keys):
                            to_deletes.setdefault(field_name, (model, set()))
                            to_deletes[field_name][1].update(unused_primary_keys)
        for field_name, (model, primary_keys) in to_deletes.items():
            model.objects.filter(pk__in=primary_keys).delete()

    def deep_process(self, datas: list[any], delete_models: list[Model]) -> list[tuple[any, any]]:
        datas_and_nesteds = [(data, {} if isinstance(data, dict) else data) for data in datas]
        self._process_forward_relations(datas_and_nesteds, delete_models)
        pks_and_representations = self.bulk_update_or_create(datas_and_nesteds)
        pks, representations = map(list, zip(*pks_and_representations))
        self._process_reverse_relations(datas, pks, representations, delete_models)
        self._clean_datas_representation(representations, delete_models)
        return pks_and_representations

    def update_or_create(self, data: dict, instances: dict[any, Model] = None) -> tuple[any, dict]:
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
            if instances is None:
                self.instance = self.Meta.model.objects.filter(pk=pk).first()
            else:
                self.instance = instances.get(pk, None)
        self.initial_data, self.partial = data, bool(self.instance)
        if self.is_valid():
            return self.save().pk, self.data
        return self._pk_error, self.errors

    def bulk_update_or_create(self, datas_and_nesteds: list[any]) -> list[tuple[any, dict]]:
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
        pk_name = self.Meta.model._meta.pk.name
        instances = self.Meta.model.objects.prefetch_related(
            *self.get_prefetch_related(depth=self.Meta.depth)).in_bulk(set(
                data[pk_name]
                for data, _ in datas_and_nesteds
                if isinstance(data, dict) and pk_name in data
            )
        )
        for data, nested in datas_and_nesteds:
            if isinstance(data, dict):
                found_pk = data.get(pk_name, None)
                if found_pk not in created:
                    pk, representation = type(self)(context=self.context).update_or_create(data, instances=instances)
                    if pk == self._pk_error:
                        representation = OrderedDict(representation, **nested, ERROR=self._pk_error)
                    else:
                        representation = OrderedDict(representation, **nested, OLD_NESTED={
                            field_name: representation[field_name]
                            for field_name in self._all_relationships
                        })
                    found_pk = found_pk if found_pk is not None else pk
                    created[found_pk] = pk, representation
                pks_and_representations.append(created[found_pk])
            else:
                pks_and_representations.append((data, nested))
        return pks_and_representations

    def deep_update_or_create(self,
                              model: Model,
                              datas: list[dict],
                              delete_models: list[Model] = [],
                              verbose: bool = True) -> list | None:
        """
        Create either a list of model or a unique model with their nested models at any depth.

        If the resulting data is too big to be sent back,
        'verbose'=False is used to only send the primary_key of the created model.
        If there has been errors it will send the dict with the errors regardless of verbose

        The deep_create work with:
        one_to_one, one_to_many, many_to_one and many_to_many relationships.
        """
        try:
            with atomic():
                primary_key, representation = map(list, zip(*self.get_serializer_class(
                    model, use_case="Deep"
                )(context=self.context).deep_process(datas, delete_models)))
                if any("ERROR" in data for data in representation if isinstance(data, dict)):
                    raise ValidationError(representation)
                return representation if verbose else primary_key
        except ValidationError as e:
            return e.detail

    @classmethod
    def get_serializer_class(cls, model: Model, use_case: str = ""):
        """
        Get back or create a serializer for the _model and its use case.
        Manually created serializer inheriting DeepViewSet will automatically be used
        for its use case.

        If your serializer is only used in a specific use-case, write it in the use_case

        model: Contain the model related to the serializer wanted
        use_case: Contain the use that this serializer will be used for,
        -> if empty, it will be the main serializer for this model
        """
        if use_case + model.__name__ not in cls._serializers:
            parent = cls.get_serializer_class(model) if use_case else DeepSerializer
            _use_case, _model = use_case, model

            class CommonSerializer(parent):
                """
                Common serializer template.
                Inherit either the DeepSerializer or the main model serializer.
                """

                class Meta:
                    model = _model
                    depth = 0
                    fields = '__all__'
                    use_case = _use_case

            CommonSerializer.__name__ = f"{_use_case}{_model.__name__}Serializer"

        return cls._serializers[use_case + model.__name__]

    def deep_create(self, data: dict | list, model: Model = None, verbose: bool = True):
        return self.deep_update_or_create(model, data, verbose=False, delete_models=[])

###################################################################################################
#
###################################################################################################
