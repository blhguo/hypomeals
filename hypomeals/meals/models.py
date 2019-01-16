from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    # This custom user class is only for future extensibilty purposes
    pass