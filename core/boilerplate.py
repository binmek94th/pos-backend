import requests
from uuid import uuid4
import bcrypt
from django.conf import settings

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

COUCHDB_URL = settings.COUCHDB_URL


def initialize_permissions(db_name):
    bulk_data = [
        {**permission, '_id': f"permission_{uuid4()}"} for permission in initial_permissions
    ]

    response = requests.post(f"{COUCHDB_URL}{db_name}/_bulk_docs", json={"docs": bulk_data})
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
    hashed_password = hash_password(SUPER_USER["password"])

    superuser_doc = {
        "_id": "superuser",
        **SUPER_USER,
        "pinCode": hashed_password
    }

    response = requests.post(f"{COUCHDB_URL}{db_name}", json=superuser_doc)
    if response.status_code != 201:
        raise Exception(f"Error creating superuser document: {response.text}")

    print("Superuser initialized in CouchDB.")
