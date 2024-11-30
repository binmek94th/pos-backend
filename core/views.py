from django.contrib.sites import requests
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from core.boilerplate import initialize_superuser, initialize_permissions
from core.models import Company, User, Backup
from core.permission import IsSuperUser
from core.serializers import CompanySerializer, UserSerializer, AdminUserSerializer, BackupSerializer
from core.couch import sanitize_database_name, generate_secure_password, create_couchdb_database, create_couchdb_user, \
    delete_couchdb_database, backup_all_databases, backup_database


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Company.objects.all()
        user = self.request.user
        company = user.company_id
        if company is None:
            return Company.objects.none()
        return Company.objects.filter(id=company)

    def get_permissions(self):
        if self.action in ['create', 'update', 'destroy']:
            self.permission_classes = [IsSuperUser]
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    @transaction.atomic
    def perform_create(self, serializer):
        if serializer.is_valid():
            if serializer.validated_data['type'] == 'on_online':
                raw_database_name = serializer.validated_data['name']
                database_name = sanitize_database_name(raw_database_name)
                database_user = f'{database_name}_user'
                database_password = generate_secure_password()

                company_instance = serializer.save(
                    name=database_name,
                )

                company_instance.database_name = database_name
                company_instance.database_user = database_user
                company_instance.database_password = database_password
                company_instance.save()

                if create_couchdb_database(database_name, database_user):
                    create_couchdb_user(database_user, database_password)
                    initialize_permissions(company_instance.database_name)
                    initialize_superuser(company_instance.database_name)

    def perform_destroy(self, instance):
        database_name = sanitize_database_name(instance.name)
        delete_couchdb_database(database_name)
        instance.delete()
        return instance

    def perform_update(self, serializer):
        if serializer.is_valid():
            company_instance = serializer.save()
            database_name = sanitize_database_name(company_instance.name)
            company_instance.name = database_name
            company_instance.save()
            database_user = company_instance.database_user
            database_password = company_instance.database_password
            create_couchdb_user(database_user, database_password)
            return company_instance


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(username=self.request.user.username)

    def get_serializer_class(self):
        if self.request.user.is_superuser:
            return AdminUserSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
            user.save()

    def perform_update(self, serializer):
        user = serializer.save()
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
            user.save()


class BackupViewSet(ModelViewSet):
    queryset = Backup.objects.all()
    serializer_class = BackupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            Backup.objects.all()
            return Backup.objects.all()
        company = self.request.user.company_id
        if company:
            return Backup.objects.filter(company_id=company)
        return Backup.objects.none()

    def perform_create(self, serializer):
        try:
            db = serializer.validated_data.get('database')
            if db:
                backup_file = backup_database(db)
                company = Company.objects.get(name=db)
                Backup.objects.create(path=backup_file, database=db, company=company)
            else:
                backups = backup_all_databases()
                for backup in backups:
                    try:
                        if backup['database_name'] == '_replicator' or backup['database_name'] == '_users':
                            Backup.objects.create(path=backup['path'], database=backup['database_name'])
                            continue
                        company = Company.objects.get(name=backup['database_name'])
                        Backup.objects.create(path=backup['path'], database=backup['database_name'], company=company)
                    except Company.DoesNotExist:
                        continue
                    except Exception as e:
                        raise Exception(f"Error saving backup: {e}")
        except Exception as e:
            raise Exception(f"Error creating backup: {e}")

    def perform_destroy(self, instance):
        raise Exception("Backups cannot be deleted.")

    def perform_update(self, serializer):
        raise Exception("Backups cannot be updated.")