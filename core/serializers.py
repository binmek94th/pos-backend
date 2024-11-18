from rest_framework import serializers
from core.models import Company, User


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['database_user', 'database_password']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['password', 'username', 'email', 'first_name', 'last_name', 'company']
        read_only_fields = ['company']
        extra_kwargs = {
            'password': {'write_only': True},
        }


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'password', 'username', 'email', 'first_name', 'last_name', 'company']
        read_only_fields = ['password']
