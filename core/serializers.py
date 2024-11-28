from rest_framework import serializers
from core.models import Company, User
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ['database_user', 'database_password']


class UserSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'password')


class UserAdminSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'company')


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'password', 'username', 'email', 'first_name', 'last_name', 'company']
        read_only_fields = ['password']

