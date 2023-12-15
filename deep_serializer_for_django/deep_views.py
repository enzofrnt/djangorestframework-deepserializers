"""
This module is used to create a unique viewset for all your need of deep read and deep write,
made easy with the help of deep_serializer
"""

from rest_framework.utils import model_meta
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .deep_serializers import DeepSerializer


###################################################################################################
#
###################################################################################################


class ReadOnlyDeepViewSet(ReadOnlyModelViewSet):
    """
    A unique viewset for all your need of deep read and deep write, made easy

    Read only version
    """
    _viewsets = {}
    _mode = "Read"

    def __init_subclass__(cls, **kwargs):
        """
        Used to save the important information like:
            -> all the viewset inheriting DeepViewSet and avoid creating already created viewset
            -> all the possible filter_fields to 'filter by' or 'order by' for this viewset
        """
        super().__init_subclass__(**kwargs)
        if cls.queryset:
            model = cls.queryset.model
            cls._viewsets[cls._mode + model.__name__] = cls
            cls._filter_fields = [p[2:] for p in cls.build_filter_fields(model, [model])]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.depth = 0

    @classmethod
    def build_filter_fields(cls, parent_model, exclude_models):
        """
        Is used to create the list of all the possible field inside this view,
            Used to check if a filter or order_by params is valid for the request

        Should never be called alone, because generate the list recursively through 
        all the nested models
        """
        reverse_relations = model_meta.get_field_info(parent_model).reverse_relations
        exclude_set = {
            n for n in reverse_relations if n.endswith("_set")
        }
        prefetch_related = []
        for field_relation in parent_model._meta.get_fields():
            if f"{field_relation.name}_set" not in exclude_set:
                current_prefetch = f"__{field_relation.name}"
                prefetch_related.append(current_prefetch)
                if (model := field_relation.related_model) and model not in exclude_models:
                    for prefetch in cls.build_filter_fields(model, exclude_models + [model]):
                        prefetch_related.append(current_prefetch + prefetch)
        return prefetch_related

    @classmethod
    def init_router(cls, router, models: list):
        """
        models: list of model to register in the router

        Is used to create all the viewset for the model in models and register 
        them inside the router
        """
        for model in models:
            router.register(
                model.__name__, 
                cls.get_view(model), 
                basename=model.__name__
            )

    def get_serializer_class(self):
        """
        Used to get the seralizer class for the current viewset for its mode,
            No mode mean it will get the main serializer for the model
        """
        return DeepSerializer.get_serializer(self.queryset.model, mode=self._mode)

    def get_queryset(self):
        """
        Is used to modify the queryset to get exactly what you want

        Filtering is made with 'field_name=value'. 
        (example: /?label=foo&name=bar)
        Filter by nested model field with 'field_name__field_name=value'. 
        (example: /?group__label=bar)
        Sorting is made with 'order_by' like 'order_by=field_name'. 
        (example: /?order_by=foo,bar)
        Display deeper model with 'depth' like 'depth=depth_level'. 
        (example: /?depth=5)
        Remove deeper model with 'exclude' like 'exclude=foo' or 'exclude=foo,bar'
        Exclude nested model of nested model like 
        'exclude=bar__foo,bar__user__group,bar__user__comments'
        And you can do it all at once. (example: /?depth=10&order_by=foo&label=bar&group=bar)
        """
        params = self.request.query_params
        serializer = self.get_serializer_class()
        serializer.Meta.depth = int(params.get("depth", self.depth))
        serializer.prefetch_related = serializer.to_prefetch_related(
            excludes=params.get("exclude", "").split(",")
        )
        queryset = self.queryset.prefetch_related(*serializer.prefetch_related)
        # Filter creation
        filter_fields = {field: value for field, value in params.items() if field in self._filter_fields}
        if filter_fields:
            queryset = queryset.filter(**filter_fields)

        # Order by creation
        order_fields = params.get("order_by", "").split(",")
        order_by = [field for field in order_fields if field in self._filter_fields]
        if order_by:
            queryset = queryset.order_by(*order_by)

        return queryset

    @classmethod
    def get_view(cls, _model, mode: str = ""):
        """
        Create a viewset for the _model and its mode if it does not exist, else it gets 
        the viewset back
        You can create your own viewset that inherit DeepViewSet, and it will be used 
        when called upon
        If your viewset is only used in a specific use-case, write it in the mode

        _model: Contain the model related to the viewset wanted
        mode: Contain the use that this viewset will be used for,
            if empty, it will be the main viewset for this model
        """
        if mode + _model.__name__ not in cls._viewsets:
            class CommonViewSet(cls):
                _mode = mode
                queryset = _model.objects
                depth = 0

            CommonViewSet.__name__ = _model.__name__
            CommonViewSet.__doc__ = f"""
            View Set for the model: '{_model.__name__}' used for {mode if mode else 'Read and Write'}

            For GET request:
            Filtering is made with 'field_name=value'. 
            (example: /?label=foo&name=bar)
            Filter by nested model field with 'field_name__field_name=value'. 
            (example: /?group__label=bar)
            Sorting is made with 'order_by' like 'order_by=field_name'. 
            (example: /?order_by=foo,bar)
            Display deeper model with 'depth' like 'depth=depth_level'. 
            (example: /?depth=5)
            Remove deeper model with 'exclude' like 'exclude=foo' or 'exclude=foo,bar'
            Exclude nested model of nested model 
            like 'exclude=bar__foo,bar__user__group,bar__user__comments'
            And you can do it all at once. 
            (example: /?depth=10&order_by=foo&label=bar&group=bar)
            """

        return cls._viewsets[mode + _model.__name__]


class DeepViewSet(ReadOnlyDeepViewSet, ModelViewSet):
    """
    A unique viewset for all your need of deep read and deep write, made easy

    Read and Write version
    """
    _mode = ""

###################################################################################################
#
###################################################################################################
