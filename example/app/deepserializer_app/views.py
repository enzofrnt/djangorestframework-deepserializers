from rest_framework import viewsets
from .models import Student
from .serializers import SimpleStudentSerializer

class SimpleStudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects
    serializer_class = SimpleStudentSerializer