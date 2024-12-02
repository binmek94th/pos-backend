import json
import os
import secrets
import string
import re
import zipfile
from datetime import datetime
import shutil
import requests
from django.conf import settings

COUCHDB_URL = settings.COUCHDB_URL
ADMIN_USER = settings.ADMIN_USER
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
BACKUP_DIR = 'backups'


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


def get_all_databases():
    response = requests.get(f"{COUCHDB_URL}/_all_dbs", auth=(ADMIN_USER, ADMIN_PASSWORD))
    response.raise_for_status()
    return response.json()


def backup_database(db_name):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    url = f"{COUCHDB_URL}/{db_name}/_all_docs?include_docs=true"
    response = requests.get(url, auth=(ADMIN_USER, ADMIN_PASSWORD))
    response.raise_for_status()
    data = response.json()

    backup_dir = os.path.join(BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.json")

    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=4)

    compressed_file = shutil.make_archive(
        os.path.join(backup_dir, f"{db_name}_{timestamp}"),
        'zip',
        backup_dir,
        f"{db_name}_{timestamp}.json"
    )

    os.remove(backup_file)

    return compressed_file


def backup_all_databases():
    databases = get_all_databases()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    dated_backup_dir = os.path.join(BACKUP_DIR)
    os.makedirs(dated_backup_dir, exist_ok=True)

    backup_paths = []

    for db_name in databases:
        try:
            url = f"{COUCHDB_URL}/{db_name}/_all_docs?include_docs=true"
            response = requests.get(url, auth=(ADMIN_USER, ADMIN_PASSWORD))
            response.raise_for_status()
            data = response.json()

            backup_file = os.path.join(dated_backup_dir, f"{db_name}_{timestamp}.json")
            with open(backup_file, 'w') as f:
                json.dump(data, f, indent=4)

            compressed_file = shutil.make_archive(
                os.path.join(dated_backup_dir, f"{db_name}_{timestamp}"),
                'zip',
                dated_backup_dir,
                f"{db_name}_{timestamp}.json"
            )

            os.remove(backup_file)

            backup_paths.append({'path': compressed_file, 'database_name': db_name})

        except requests.exceptions.RequestException as e:
            print(f"Error backing up database '{db_name}': {e}")
        except Exception as e:
            print(f"Unexpected error for database '{db_name}': {e}")

    return backup_paths


def restore_database(zip_file_path, db_name):
    if not os.path.exists(zip_file_path):
        raise FileNotFoundError(f"The backup file {zip_file_path} does not exist.")

    temp_dir = os.path.join(BACKUP_DIR, "temp_restore")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        dir_name, file_name = os.path.split(zip_file_path)
        file_name_json = file_name.split('.')[0] + '.json'

        new_dir = os.path.join(dir_name, 'temp_restore')

        new_file_path = os.path.join(new_dir, file_name_json)

        if not os.path.exists(new_file_path):
            raise FileNotFoundError(f"No JSON file found for the database '{db_name}'.")

        with open(new_file_path, 'r') as f:
            backup_data = json.load(f)

        url = f"{COUCHDB_URL}/{db_name}"
        response = requests.get(url, auth=(ADMIN_USER, ADMIN_PASSWORD))

        if response.status_code == 404:
            response = requests.put(url, auth=(ADMIN_USER, ADMIN_PASSWORD))
            if response.status_code != 201:
                raise Exception(f"Failed to create database {db_name}: {response.text}")

        docs = backup_data.get("rows", [])
        delete_and_recreate_database(db_name)
        insert_url = f"{COUCHDB_URL}/{db_name}/_bulk_docs"
        response = requests.post(insert_url, json={"docs": docs}, auth=(ADMIN_USER, ADMIN_PASSWORD))
        if response.status_code != 201:
            raise Exception(f"Failed to restore database {db_name}: {response.text}")

        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(temp_dir)

        return f"Database '{db_name}' successfully restored from {zip_file_path}"

    except Exception as e:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(temp_dir)
        raise e


def delete_and_recreate_database(db_name):
    delete_url = f"{COUCHDB_URL}/{db_name}"
    delete_response = requests.delete(delete_url, auth=(ADMIN_USER, ADMIN_PASSWORD))

    if delete_response.status_code != 200:
        raise Exception(f"Failed to delete database {db_name}: {delete_response.text}")

    create_url = f"{COUCHDB_URL}/{db_name}"
    create_response = requests.put(create_url, auth=(ADMIN_USER, ADMIN_PASSWORD))

    if create_response.status_code == 201:
        database_user = f'{db_name}_user'
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

        security_url = f"{COUCHDB_URL}{db_name}/_security"
        security_response = requests.put(security_url, json=security_doc, auth=(ADMIN_USER, ADMIN_PASSWORD))

        if security_response.status_code == 200:
            print(f"Security for database '{db_name}' set for user '{database_user}'.")
            return True

    if create_response.status_code != 201:
        raise Exception(f"Failed to recreate database {db_name}: {create_response.text}")

    print(f"Successfully deleted and recreated the database {db_name}.")