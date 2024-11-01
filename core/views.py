import couchdb
import secrets
import string
import re
import requests
from django.db import transaction
from rest_framework.viewsets import ModelViewSet
from core.models import Company
from core.serializers import CompanySerializer

server = couchdb.Server('http://admin:secret@localhost:5984/')


def sanitize_database_name(name):
    return re.sub(r'[^a-z0-9_]', '_', name.lower())


def generate_secure_password(length=12):
    characters = string.ascii_letters
    return ''.join(secrets.choice(characters) for _ in range(length))


def create_couchdb_database(database_name, database_user, database_password):
    try:
        db = server.create(database_name)

        security_doc = {
            "admins": {
                "names": [database_user],
                "roles": []
            },
            "members": {
                "names": [database_user],
                "roles": []
            }
        }

        url = f"http://admin:secret@localhost:5984/{database_name}/_security"
        response = requests.put(url, json=security_doc)

        if response.status_code == 200:
            print(f"Database '{database_name}' created and secured for user '{database_user}'.")
            return True
        else:
            raise Exception(f"Failed to set security for database '{database_name}': {response.text}")

    except couchdb.http.PreconditionFailed:
        print(f"Database '{database_name}' already exists.")
        return False
    except Exception as e:
        print(f"An error occurred while creating the database: {e}")
        raise


def create_couchdb_user(database_user, database_password):
    users_db = server['_users']

    user_doc = {
        "_id": f"org.couchdb.user:{database_user}",
        "name": database_user,
        "password": database_password,
        "roles": [],
        "type": "user"
    }

    try:
        users_db.save(user_doc)
        print(f"User '{database_user}' created successfully.")
    except couchdb.http.ResourceConflict:
        print(f"User '{database_user}' already exists.")
    except Exception as e:
        print(f"Error creating user '{database_user}': {e}")


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_queryset(self):
        return Company.objects.all()

    @transaction.atomic
    def perform_create(self, serializer):
        if serializer.is_valid():
            if serializer.validate_data['type'] == 'on_premise':
                pass
            raw_database_name = serializer.validated_data['name']
            database_name = sanitize_database_name(raw_database_name)
            database_user = f'{database_name}_user'
            database_password = generate_secure_password()

            serializer.validated_data['database_user'] = database_user
            serializer.validated_data['database_password'] = database_password
            company_instance = serializer.save()

            if create_couchdb_database(database_name, database_user, database_password):
                create_couchdb_user(database_user, database_password)

    def perform_destroy(self, instance):
        database_name = sanitize_database_name(instance.name)
        server.delete(database_name)
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
