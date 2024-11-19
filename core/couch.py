import secrets
import string
import re
import requests
from django.conf import settings

COUCHDB_URL = settings.COUCHDB_URL
ADMIN_USER = settings.ADMIN_USER
ADMIN_PASSWORD = settings.ADMIN_PASSWORD


def sanitize_database_name(name):
    return re.sub(r'[^a-z0-9_]', '_', name.lower())


def generate_secure_password(length=12):
    characters = string.ascii_letters
    return ''.join(secrets.choice(characters) for _ in range(length))


def create_couchdb_database(database_name, database_user):
    sanitized_name = sanitize_database_name(database_name)

    create_url = f"{COUCHDB_URL}{sanitized_name}"
    response = requests.put(create_url, auth=(ADMIN_USER, ADMIN_PASSWORD))

    if response.status_code == 201:
        print(f"Database '{sanitized_name}' created successfully.")

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

        security_url = f"{COUCHDB_URL}{sanitized_name}/_security"
        security_response = requests.put(security_url, json=security_doc, auth=(ADMIN_USER, ADMIN_PASSWORD))

        if security_response.status_code == 200:
            print(f"Security for database '{sanitized_name}' set for user '{database_user}'.")
            return True
        else:
            raise Exception(f"Failed to set security for database '{sanitized_name}': {security_response.text}")
    elif response.status_code == 412:
        print(f"Database '{sanitized_name}' already exists.")
        return False
    else:
        raise Exception(f"Failed to create database '{sanitized_name}': {response.text}")


def create_couchdb_user(database_user, database_password):
    users_url = f"{COUCHDB_URL}_users"

    user_doc = {
        "_id": f"org.couchdb.user:{database_user}",
        "name": database_user,
        "password": database_password,
        "roles": [],
        "type": "user"
    }

    response = requests.post(users_url, json=user_doc, auth=(ADMIN_USER, ADMIN_PASSWORD))

    if response.status_code == 201:
        print(f"User '{database_user}' created successfully.")
    elif response.status_code == 409:
        print(f"User '{database_user}' already exists.")
    else:
        print(f"Error creating user '{database_user}': {response.text}")


def delete_couchdb_database(database_name):
    sanitized_name = sanitize_database_name(database_name)

    delete_url = f"{COUCHDB_URL}{sanitized_name}"
    response = requests.delete(delete_url, auth=(ADMIN_USER, ADMIN_PASSWORD))

    if response.status_code == 200:
        print(f"Database '{sanitized_name}' deleted successfully.")
    elif response.status_code == 404:
        print(f"Database '{sanitized_name}' does not exist.")
    else:
        print(f"Error deleting database '{sanitized_name}': {response.text}")
