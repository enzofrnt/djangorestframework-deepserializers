from django.db import models

class HighSchool(models.Model):
    secure = False
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=100)

class Class(models.Model):
    secure = False
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    high_school = models.ForeignKey(HighSchool, on_delete=models.CASCADE, related_name='classes')

class Student(models.Model):
    secure = True

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    class_field = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')