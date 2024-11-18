import secrets
import string
import re
import requests
import couchdb
from posBackend.settings import COUCHDB_URL

server = couchdb.Server(COUCHDB_URL)


def sanitize_database_name(name):
    return re.sub(r'[^a-z0-9_]', '_', name.lower())


def generate_secure_password(length=12):
    characters = string.ascii_letters
    return ''.join(secrets.choice(characters) for _ in range(length))


def create_couchdb_database(database_name, database_user):
    try:
        server.create(database_name)

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


def delete_couchdb_database(database_name):
    try:
        server.delete(database_name)
        print(f"Database '{database_name}' deleted successfully.")
    except couchdb.http.ResourceNotFound:
        print(f"Database '{database_name}' does not exist.")
    except Exception as e:
        print(f"An error occurred while deleting the database: {e}")
        raise
