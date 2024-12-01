from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser, Group, Permission


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True)


class Type(models.TextChoices):
    ON_PREMISE = 'on_premise'
    ON_ONLINE = 'on_online'


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    database_user = models.CharField(max_length=255)
    database_password = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=Type.choices, default=Type.ON_PREMISE)

    def __str__(self):
        return self.name


class Backup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    database = models.CharField(max_length=255, blank=True)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    path = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True, blank=True)
