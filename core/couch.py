import json
import os
import secrets
import string
import re
from datetime import datetime
import shutil
import requests
from django.conf import settings
from django.http import JsonResponse

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
    url = f"{COUCHDB_URL}/{db_name}/_all_docs?include_docs=true"
    response = requests.get(url, auth=(ADMIN_USER, ADMIN_PASSWORD))
    response.raise_for_status()
    data = response.json()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    backup_dir = os.path.join(BACKUP_DIR, "single-backups", timestamp)
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = os.path.join(backup_dir, f"{db_name}.json")

    with open(backup_file, 'w') as f:
        json.dump(data, f, indent=4)

    compressed_file = shutil.make_archive(
        os.path.join(backup_dir, f"{db_name}"),
        'zip',
        backup_dir,
        f"{db_name}.json"
    )

    os.remove(backup_file)

    return compressed_file


def backup_all_databases():
    databases = get_all_databases()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dated_backup_dir = os.path.join(BACKUP_DIR, "all", timestamp)
    os.makedirs(dated_backup_dir, exist_ok=True)

    for db_name in databases:
        try:
            url = f"{COUCHDB_URL}/{db_name}/_all_docs?include_docs=true"
            response = requests.get(url, auth=(ADMIN_USER, ADMIN_PASSWORD))
            response.raise_for_status()
            data = response.json()

            backup_file = os.path.join(dated_backup_dir, f"{db_name}.json")
            with open(backup_file, 'w') as f:
                json.dump(data, f, indent=4)

            compressed_file = shutil.make_archive(
                os.path.join(dated_backup_dir, f"{db_name}"),
                'zip',
                dated_backup_dir,
                f"{db_name}.json"
            )

            os.remove(backup_file)

        except requests.exceptions.RequestException as e:
            print(f"Error backing up database '{db_name}': {e}")
        except Exception as e:
            print(f"Unexpected error for database '{db_name}': {e}")

    return dated_backup_dir


def get_backup_files_from_dir(directory):
    dated_backups = []
    for dated_folder in os.listdir(directory):
        folder_path = os.path.join(directory, dated_folder)
        if os.path.isdir(folder_path):
            backup_files = [
                f for f in os.listdir(folder_path) if f.endswith('.zip')
            ]
            for backup_file in backup_files:
                formatted_date = format_date(dated_folder)
                dated_backups.append({
                    'date': formatted_date,
                    'backups': backup_file
                })
    return dated_backups


def list_backups(request):
    try:
        single_backup_dir = os.path.join(BACKUP_DIR, "single-backups")
        all_backup_dir = os.path.join(BACKUP_DIR, "all")

        single_backups = get_backup_files_from_dir(single_backup_dir)
        all_backups = get_backup_files_from_dir(all_backup_dir)

        all_backups_combined = single_backups + all_backups

        return JsonResponse(all_backups_combined, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def format_date(date_string):

    try:
        parsed_date = datetime.strptime(date_string, "%Y%m%d_%H%M%S")
        return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return date_string