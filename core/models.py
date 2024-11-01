from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser, Group, Permission


class User(AbstractUser):
    email = models.EmailField(unique=True)
    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []


    def __str__(self):
        return self.email


class Type(models.TextChoices):
    ON_PREMISE = 'on_premise'
    ON_ONLINE = 'on_online'


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    database_user = models.CharField(max_length=255)
    database_password = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=Type.choices)
