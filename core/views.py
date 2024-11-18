from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.boilerplate import initialize_superuser, initialize_permissions
from core.models import Company, User
from core.permission import IsSuperUser
from core.serializers import CompanySerializer, UserSerializer, AdminUserSerializer
from core.couch import sanitize_database_name, generate_secure_password, create_couchdb_database, create_couchdb_user, \
    delete_couchdb_database


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
            if serializer.validated_data['type'] == 'on_premise':
                pass

            raw_database_name = serializer.validated_data['name']
            database_name = sanitize_database_name(raw_database_name)
            database_user = f'{database_name}_user'
            database_password = generate_secure_password()

            company_instance = serializer.save()

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
