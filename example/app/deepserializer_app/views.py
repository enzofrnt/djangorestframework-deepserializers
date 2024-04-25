from rest_framework import viewsets
from .models import Student, Class
from .serializers import SimpleStudentSerializer, SimpleClassSerializer
from deepserializers import ModelDeepViewSet

class SimpleStudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects
    serializer_class = SimpleStudentSerializer

class SimpleClassViewSet(ModelDeepViewSet):
    queryset = Class.objects
    serializer_class = SimpleClassSerializer