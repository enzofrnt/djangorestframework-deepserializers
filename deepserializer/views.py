"""
A unique viewset for all your need of deep read and deep write, made easy
"""
from django.db.models import Model
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
            cls._possible_fields = cls.build_possible_fields(model, [])

    @classmethod
    def build_possible_fields(cls, parent_model: Model, excludes: list[Model]) -> set[str]:
        """
        Create the list of all the possible fields for this view,
        Used to check if a string can be used for filtering or ordering a queryset
        """
        possible_fields = set()
        for field_relation in parent_model._meta.get_fields():
            if (model := field_relation.related_model) not in excludes:
                field_name = field_relation.name
                possible_fields.add(field_name)
                if model:
                    possible_fields.update((
                        f"{field_name}__{field}"
                        for field in cls.build_possible_fields(model, excludes + [parent_model])
                    ))
        return possible_fields

    @classmethod
    def init_router(cls, router, models: list) -> None:
        """
        Create all the viewset for the models and register them in the router

        router: Should be a rest_framework router
        models: list of model to register in the router
        """
        for model in models:
            router.register(model.__name__, cls.get_view(model), basename=model.__name__)

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        params = self.request.query_params
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        depth = int(params.get("depth", self.depth))
        return serializer_class(
            *args,
            depth=depth,
            relations_paths=serializer_class.get_relations_paths(
                excludes=params.get("exclude", "").split(","),
                depth=depth
            ),
            **kwargs
        )

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
        serializer = self.get_serializer()
        queryset = serializer.optimize_queryset(self.queryset)
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
