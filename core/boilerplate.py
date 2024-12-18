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
    {'name': 'Permission_group', 'type': 'permission', 'is_active': False, 'permission_id': 15},
    {'name': 'Inventory_movement', 'type': 'permission', 'is_active': False, 'permission_id': 16},
    {'name': 'Inventory_category', 'type': 'permission', 'is_active': False, 'permission_id': 17},
    {'name': 'Inventory_product', 'type': 'permission', 'is_active': False, 'permission_id': 18},
    {'name': 'Printer', 'type': 'permission', 'is_active': False, 'permission_id': 19},
    {'name': 'Setting', 'type': 'permission', 'is_active': False, 'permission_id': 20},
]

initial_settings = [
    {'name': 'Waiter', 'value': False},
    {'name': 'Customer', 'value': False},
    {'name': 'Inventory', 'value': False},
    ]

COUCHDB_URL = settings.COUCHDB_URL


def initialize_settings(db_name):
    bulk_data = [
        {**setting, '_id': f"setting_{uuid4()}"} for setting in initial_settings
    ]

    response = requests.post(f"{COUCHDB_URL}{db_name}/_bulk_docs", json={"docs": bulk_data})
    if response.status_code != 201:
        raise Exception(f"Error creating setting documents: {response.text}")

    print("Settings initialized in CouchDB.")


def initialize_permissions(db_name):
    bulk_data = [
        {**permission, '_id': f"permission_{uuid4()}"} for permission in initial_permissions
    ]

    response = requests.post(f"{COUCHDB_URL}{db_name}/_bulk_docs", json={"docs": bulk_data})
    if response.status_code != 201:
        raise Exception(f"Error creating permission documents: {response.text}")

    print("Permissions initialized in CouchDB.")


SUPER_USER = {
    "_id": f"user_{uuid4()}",
    "name": "Super User",
    "is_active": True,
    "type": "user",
    "password": "12345",
    "admin": True,
}


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')


def initialize_superuser(db_name):
    hashed_password = hash_password(SUPER_USER["password"])

    superuser_doc = {
        **SUPER_USER,
        "pinCode": hashed_password
    }

    response = requests.post(f"{COUCHDB_URL}{db_name}", json=superuser_doc)
    if response.status_code != 201:
        raise Exception(f"Error creating superuser document: {response.text}")

    print("Superuser initialized in CouchDB.")
