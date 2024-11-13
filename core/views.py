from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from core.models import Company
from core.permission import IsSuperUser
from core.serializers import CompanySerializer
from core.couch import sanitize_database_name, generate_secure_password, create_couchdb_database, create_couchdb_user, \
    delete_couchdb_database
import requests
from uuid import uuid4
import bcrypt


class CompanyViewSet(ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

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

initial_permissions = [
    {'name': 'Location', 'type': 'permission', 'is_active': False, 'permission_id': 1},
    {'name': 'Category', 'type': 'permission', 'is_active': False, 'permission_id': 2},
    {'name': 'Products', 'type': 'permission', 'is_active': False, 'permission_id': 3},
    {'name': 'Product_modifier', 'type': 'permission', 'is_active': False, 'permission_id': 4},
    {'name': 'Discount', 'type': 'permission', 'is_active': False, 'permission_id': 5},
    {'name': 'Session', 'type': 'permission', 'is_active': False, 'permission_id': 6},
    {'name': 'User', 'type': 'permission', 'is_active': False, 'permission_id': 7},
    {'name': 'POS', 'type': 'permission', 'is_active': False, 'permission_id': 8},
    {'name': 'Order', 'type': 'permission', 'is_active': False, 'permission_id': 9},
    {'name': 'Refund', 'type': 'permission', 'is_active': False, 'permission_id': 10},
    {'name': 'Entity_category', 'type': 'permission', 'is_active': False, 'permission_id': 11},
    {'name': 'Entity', 'type': 'permission', 'is_active': False, 'permission_id': 12},
    {'name': 'Customer', 'type': 'permission', 'is_active': False, 'permission_id': 13},
    {'name': 'Account', 'type': 'permission', 'is_active': False, 'permission_id': 14},
]


def initialize_permissions(db_name):
    couch_db_url = "http://admin:secret@localhost:5984/"

    response = requests.get(f"{couch_db_url}/{db_name}")
    if response.status_code == 404:
        response = requests.put(f"{couch_db_url}/{db_name}")
        if response.status_code != 201:
            raise Exception("Error creating CouchDB database")

    bulk_data = [
        {**permission, '_id': f"permission_{uuid4()}"} for permission in initial_permissions
    ]

    response = requests.post(f"{couch_db_url}/{db_name}/_bulk_docs", json={"docs": bulk_data})
    if response.status_code != 201:
        raise Exception(f"Error creating permission documents: {response.text}")

    print("Permissions initialized in CouchDB.")


SUPER_USER = {
    "_id": f"user{uuid4()}",
    "name": "Super User",
    "is_active": True,
    "type": "user",
    "password": "12345",
}


def hash_password(password: str) -> str:

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')


def initialize_superuser(db_name):
    couch_db_url = "http://admin:secret@localhost:5984/"

    response = requests.get(f"{couch_db_url}/{db_name}/superuser")
    if response.status_code == 404:
        hashed_password = hash_password(SUPER_USER["password"])

        superuser_doc = {
            "_id": "superuser",
            **SUPER_USER,
            "pinCode": hashed_password
        }

        response = requests.post(f"{couch_db_url}/{db_name}", json=superuser_doc)
        if response.status_code != 201:
            raise Exception(f"Error creating superuser document: {response.text}")

        print("Superuser initialized in CouchDB.")
    else:
        print("Superuser already exists in CouchDB.")
