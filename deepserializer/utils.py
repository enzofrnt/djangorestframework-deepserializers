from typing import Type
from django.db.models import Model

class ModelInfo:
    def __init__(self, model: Type[Model], secure: bool = True):
        self.model = model
        self.secure = secure