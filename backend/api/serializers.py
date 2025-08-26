from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Renter, Host, Wallet, Transaction, GPU, Session


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id', 'username', 'first_name', 'last_name', 'email']


class RenterSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.SerializerMethodField()
    user = UserPublicSerializer(read_only=True)
    
    class Meta:
        model = Renter
        fields = ['id', 'user', 'wallet_balance']
        read_only_fields = ['id', 'user', 'wallet_balance']
    
    def get_wallet_balance(self, obj):
        try:
            return obj.get_wallet().balance
        except:
            return 0.00


class HostSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.SerializerMethodField()
    user = UserPublicSerializer(read_only=True)
    
    class Meta:
        model = Host
        fields = ['id', 'user', 'wallet_balance']
        read_only_fields = ['id', 'user', 'wallet_balance']
    
    def get_wallet_balance(self, obj):
        try:
            return obj.get_wallet().balance
        except:
            return 0.00


class WalletSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'currency', 'owner_name', 'owner_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_owner_name(self, obj):
        return obj.get_owner_name()
    
    def get_owner_type(self, obj):
        if obj.renter:
            return 'Renter'
        elif obj.host:
            return 'Host'
        return 'Unknown'


class TransactionSerializer(serializers.ModelSerializer):
    wallet_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = ['id', 'wallet', 'transaction_type', 'amount', 'status', 'description', 'wallet_owner', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_wallet_owner(self, obj):
        return obj.wallet.get_owner_name()


class GPUSerializer(serializers.ModelSerializer):
    host_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GPU
        fields = ['id', 'host', 'host_name', 'gpu_name', 'gpu_model', 'gpu_memory', 'gpu_price', 'gpu_availability', 'gpu_location', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_host_name(self, obj):
        return obj.host.user.get_full_name() or obj.host.user.username


class SessionSerializer(serializers.ModelSerializer):
    gpu_name = serializers.CharField(source='gpu.gpu_name', read_only=True)
    renter_name = serializers.SerializerMethodField()
    host_name = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    ssh_connection_string = serializers.SerializerMethodField()
    session_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'gpu', 'gpu_name', 'renter', 'renter_name', 'host', 'host_name',
            'start_time', 'end_time', 'status', 'connection_status',
            'ssh_host', 'ssh_port', 'ssh_username', 'ssh_password',
            'connection_error', 'last_connected',
            'gpu_utilization', 'memory_utilization', 'temperature',
            'is_auto_reconnect', 'payment_transaction',
            'total_cost', 'ssh_connection_string', 'session_duration',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_cost', 'ssh_connection_string', 'session_duration']
        extra_kwargs = {
            'ssh_password': {'write_only': True}
        }
    
    def get_total_cost(self, obj):
        return obj.total_cost
    
    def get_ssh_connection_string(self, obj):
        return obj.get_ssh_connection_string()
    
    def get_session_duration(self, obj):
        from django.utils import timezone
        if obj.end_time:
            duration = obj.end_time - obj.start_time
        else:
            duration = timezone.now() - obj.start_time
        
        hours = duration.total_seconds() / 3600
        return round(hours, 2)

    def get_renter_name(self, obj):
        return obj.renter.user.get_full_name() or obj.renter.user.username

    def get_host_name(self, obj):
        return obj.host.user.get_full_name() or obj.host.user.username


# Nested Serializers for detailed views
class WalletDetailSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'currency', 'owner_name', 'transactions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_owner_name(self, obj):
        return obj.get_owner_name()


class RenterDetailSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer(read_only=True)
    user = UserPublicSerializer(read_only=True)
    
    class Meta:
        model = Renter
        fields = ['id', 'user', 'wallet']
        read_only_fields = ['id']


class HostDetailSerializer(serializers.ModelSerializer):
    wallet = WalletSerializer(read_only=True)
    user = UserPublicSerializer(read_only=True)
    
    class Meta:
        model = Host
        fields = ['id', 'user', 'wallet']
        read_only_fields = ['id']


class SessionDetailSerializer(serializers.ModelSerializer):
    gpu = GPUSerializer(read_only=True)
    renter = RenterSerializer(read_only=True)
    host = HostSerializer(read_only=True)
    payment_transaction = TransactionSerializer(read_only=True)
    total_cost = serializers.SerializerMethodField()
    ssh_connection_string = serializers.SerializerMethodField()
    session_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Session
        fields = [
            'id', 'gpu', 'renter', 'host', 'start_time', 'end_time', 'status',
            'connection_status', 'ssh_host', 'ssh_port', 'ssh_username',
            'connection_error', 'last_connected', 'gpu_utilization',
            'memory_utilization', 'temperature', 'is_auto_reconnect',
            'payment_transaction', 'total_cost', 'ssh_connection_string',
            'session_duration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_cost', 'ssh_connection_string', 'session_duration']
    
    def get_total_cost(self, obj):
        return obj.total_cost
    
    def get_ssh_connection_string(self, obj):
        return obj.get_ssh_connection_string()
    
    def get_session_duration(self, obj):
        from django.utils import timezone
        if obj.end_time:
            duration = obj.end_time - obj.start_time
        else:
            duration = timezone.now() - obj.start_time
        
        hours = duration.total_seconds() / 3600
        return round(hours, 2)


# Specialized Serializers for specific operations
class SessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            'gpu', 'renter', 'host', 'start_time', 'ssh_host', 'ssh_port',
            'ssh_username', 'ssh_password', 'is_auto_reconnect'
        ]
        extra_kwargs = {
            'ssh_password': {'write_only': True}
        }
    
    def validate(self, data):
        # Check if GPU is available
        if not data['gpu'].gpu_availability:
            raise serializers.ValidationError("GPU is not available for rent")
        
        # Check if renter has sufficient balance
        renter = data['renter']
        gpu = data['gpu']
        wallet = renter.get_wallet()
        
        if wallet.balance < gpu.gpu_price:
            raise serializers.ValidationError("Insufficient balance to rent this GPU")
        
        return data


class SessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            'end_time', 'status', 'connection_status', 'connection_error',
            'gpu_utilization', 'memory_utilization', 'temperature'
        ]


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'description']


class RenterWalletSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    class Meta:
        model = Renter
        fields = ['id', 'user']
        read_only_fields = ['id', 'user']


class HostWalletSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    class Meta:
        model = Host
        fields = ['id', 'user']
        read_only_fields = ['id', 'user']
