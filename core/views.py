from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from core.models import Company
from core.permission import IsSuperUser
from core.serializers import CompanySerializer
from core.couch import sanitize_database_name, generate_secure_password, create_couchdb_database, create_couchdb_user, \
    delete_couchdb_database


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_queryset(self):
        return Company.objects.all()

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
