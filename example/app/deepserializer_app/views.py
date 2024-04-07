from django.shortcuts import render
from deepserializer import DeepViewSet
from .serializers import studentserializer,basicstudentserializer
from rest_framework import status
from rest_framework.response import Response
from .models import Student
from rest_framework.viewsets import ModelViewSet

class sudentview(DeepViewSet):
    serializer_class = studentserializer
    queryset = Student.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer()
        results = serializer.deep_update_or_create(
            self.queryset.model,
            [request.data],
        )
        if any("ERROR" in item for item in results if isinstance(item, dict)):
            return Response(results, status=status.HTTP_409_CONFLICT)
        return Response(results, status=status.HTTP_201_CREATED)
    
class basicstudentview(ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = basicstudentserializer