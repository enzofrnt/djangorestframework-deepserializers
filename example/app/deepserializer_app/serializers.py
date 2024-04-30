from rest_framework import serializers
from .models import Student, Class
from deepserializers import DeepSerializer

class SimpleStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ('name', 'age')

class SimpleClassSerializer(DeepSerializer):
    class Meta:
        model = Class
        # fields = '__all__'
        # fields = ('name', 'students')
        # exclude = ('students',)
        # students_fields = ('name', 'age')
        depth = 0