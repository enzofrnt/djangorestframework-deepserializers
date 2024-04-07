from deepserializer import DeepSerializer
from .models import Student
from rest_framework import serializers


class studentserializer(DeepSerializer):
    class Meta:
        model = Student
        fields = '__all__'
        depth = 0
        
class basicstudentserializer(serializers.Serializer):
    class Meta:
        model = Student
        fields = '__all__'
