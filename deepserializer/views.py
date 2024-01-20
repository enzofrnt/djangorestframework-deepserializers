"""
A unique viewset for all your need of deep read and deep write, made easy
"""

from rest_framework.utils import model_meta
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .serializers import DeepSerializer


###################################################################################################
#
###################################################################################################


class ReadOnlyDeepViewSet(ReadOnlyModelViewSet):
    """
    A unique viewset for all your need of deep read and deep write, made easy

    Read only version
    """
    _viewsets = {}
    use_case = "Read"
    depth = 0
    exclude_nesteds = []

    def __init_subclass__(cls, **kwargs):
        """
        Used to save the important information like:
        -> all the viewset inheriting this class
        -> all the possible fields to 'filter by' or 'order by' the queryset
        """
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'queryset') and cls.queryset is not None:
            model = cls.queryset.model
            cls._viewsets[cls.use_case + model.__name__] = cls
            cls._possible_fields = [
                field_name[2:]
                for field_name in cls.build_filter_fields(model, [model])
            ]

    @classmethod
    def build_filter_fields(cls, parent_model, exclude_models: list) -> list[str]:
        """
        Create the list of all the possible fields for this view,
        Used to check if a string can be used for filtering or ordering a queryset
        """
        exclude_set = {
            field_name
            for field_name in model_meta.get_field_info(parent_model).reverse_relations
            if field_name.endswith("_set")
        }
        prefetch_related = []
        for field_relation in parent_model._meta.get_fields():
            if f"{field_relation.name}_set" not in exclude_set:
                current_prefetch = f"__{field_relation.name}"
                prefetch_related.append(current_prefetch)
                if (model := field_relation.related_model)and model not in exclude_models:
                    for prefetch in cls.build_filter_fields(model, exclude_models + [model]):
                        prefetch_related.append(current_prefetch + prefetch)
        return prefetch_related

    @classmethod
    def init_router(cls, router, models: list) -> None:
        """
        Create all the viewset for the models and register them in the router

        router: Should be a rest_framework router
        models: list of model to register in the router
        """
        for model in models:
            router.register(model.__name__, cls.get_view(model), basename=model.__name__)

    def get_serializer_class(self):
        """
        Get the seralizer class for this viewset and its use_case,
        No use_case mean it will get the main serializer for the model
        """
        return DeepSerializer.get_serializer_class(self.queryset.model, use_case=self.use_case)

    def get_queryset(self):
        """
        Is used to modify the queryset to get exactly what you want

        Filtering is made with 'field_name=value'.
        -> Example: /?lastname=Doe&age=30
        Filter by nested model field with 'field_name__field_name=value'.
        -> Example: /?group__label=bar
        Sorting is made with 'order_by' like 'order_by=field_name'.
        If order_by is a list, it will sort in the list order.
        -> Example: /?order_by=lastname,firstname
        Display deeper model with 'depth' like 'depth=level'.
        -> Example: /?depth=5)
        Remove deeper model with 'exclude' like 'exclude=foo,bar'.
        If the nested model to exclude is nested in a nested model, separate them with '__'
        -> Example: /?exclude=job,user__group,user__comments__status
        """
        params = self.request.query_params
        serializer = self.get_serializer_class()
        serializer.Meta.depth = int(params.get("depth", self.depth))
        serializer.prefetch_related = serializer.get_prefetch_related(
            excludes=params.get("exclude", ",".join(self.exclude_nesteds)).split(","))
        queryset = self.queryset.prefetch_related(*serializer.prefetch_related)
        if filter_by := {
            field: value
            for field, value in params.items()
            if field in self._possible_fields
        }:
            queryset = queryset.filter(**filter_by)
        if order_by := [
            field
            for field in params.get("order_by", "").split(",")
            if field in self._possible_fields
        ]:
            queryset = queryset.order_by(*order_by)
        return queryset

    @classmethod
    def get_view(cls, _model, use_case: str = ""):
        """
        Get back or create a viewset for the _model and its use_case.
        Manually created viewset inheriting DeepViewSet will automatically be used for its use_case

        If your viewset is only used in a specific use-case, write it in the use_case

        _model: Contain the model related to the viewset wanted
        use_case: Contain the use that this viewset will be used for,
            if empty, it will be the main viewset for this model
        """
        if use_case + _model.__name__ not in cls._viewsets:
            _use_case = use_case

            class CommonViewSet(cls):
                """
                For GET request:
                Filtering is made with 'field_name=value'.
                -> Example: /?lastname=Doe&age=30
                Filter by nested model field with 'field_name__field_name=value'.
                -> Example: /?group__label=bar
                Sorting is made with 'order_by' like 'order_by=field_name'.
                If order_by is a list, it will sort in the list order.
                -> Example: /?order_by=lastname,firstname
                Display deeper model with 'depth' like 'depth=level'.
                -> Example: /?depth=5)
                Remove deeper model with 'exclude' like 'exclude=foo,bar'.
                Separate them with '__' if the model to exclude is in a nested model
                -> Example: /?exclude=job,user__group,user__comments__status
                """
                use_case = _use_case
                queryset = _model.objects

            CommonViewSet.__name__ = _model.__name__
            CommonViewSet.__doc__ = f"""
            View Set for the model: '{_model.__name__}'
            Used for {use_case if use_case else 'Read and Write'}
            
            """ + CommonViewSet.__doc__

        return cls._viewsets[use_case + _model.__name__]


class DeepViewSet(ReadOnlyDeepViewSet, ModelViewSet):
    """
    A unique viewset for all your need of deep read and deep write, made easy

    Read and Write version
    """
    use_case = ""

###################################################################################################
#
###################################################################################################
