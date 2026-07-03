import uuid
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Renter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='renter_profile')
    
    def __str__(self):
        name = self.user.get_full_name() or self.user.username or str(self.user)
        return f"{name} - {self.user.email}"
    
    def get_wallet(self):
        """Get or create wallet for renter"""
        wallet, created = Wallet.objects.get_or_create(renter=self)
        return wallet
    
    def add_money(self, amount, description="Deposit"):
        """Add money to renter's wallet"""
        with transaction.atomic():
            wallet = self.get_wallet()
            wallet.balance += Decimal(str(amount))
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='DEPOSIT',
                amount=amount,
                description=description
            )
            return wallet.balance
    
    def pay_for_rental(self, amount, description="Rental payment"):
        """Pay for GPU rental"""
        with transaction.atomic():
            wallet = self.get_wallet()
            if wallet.balance < Decimal(str(amount)):
                raise ValueError("Insufficient balance")
            
            wallet.balance -= Decimal(str(amount))
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='RENTAL_PAYMENT',
                amount=amount,
                description=description
            )
            return wallet.balance

class Host(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='host_profile')
    
    def __str__(self):
        name = self.user.get_full_name() or self.user.username or str(self.user)
        return f"{name} - {self.user.email}"
    
    def get_wallet(self):
        """Get or create wallet for host"""
        wallet, created = Wallet.objects.get_or_create(host=self)
        return wallet
    
    def add_earning(self, amount, description="Rental earning"):
        """Add earning from GPU rental"""
        with transaction.atomic():
            wallet = self.get_wallet()
            wallet.balance += Decimal(str(amount))
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='RENTAL_EARNING',
                amount=amount,
                description=description
            )
            return wallet.balance
    
    def withdraw_money(self, amount, description="Withdrawal"):
        """Withdraw money from host's wallet"""
        with transaction.atomic():
            wallet = self.get_wallet()
            if wallet.balance < Decimal(str(amount)):
                raise ValueError("Insufficient balance")
            
            wallet.balance -= Decimal(str(amount))
            wallet.save()
            
            # Create transaction record
            Transaction.objects.create(
                wallet=wallet,
                transaction_type='WITHDRAWAL',
                amount=amount,
                description=description
            )
            return wallet.balance

class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    renter = models.OneToOneField(Renter, on_delete=models.CASCADE, null=True, blank=True)
    host = models.OneToOneField(Host, on_delete=models.CASCADE, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='NPR')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.renter:
            owner_name = self.renter.user.get_full_name() or self.renter.user.username
            return f"Wallet - {owner_name}"
        elif self.host:
            owner_name = self.host.user.get_full_name() or self.host.user.username
            return f"Wallet - {owner_name}"
        return f"Wallet - {self.id}"
    
    def get_owner_name(self):
        """Get the name of the wallet owner"""
        if self.renter:
            name = self.renter.user.get_full_name() or self.renter.user.username
            return f"Renter: {name}"
        elif self.host:
            name = self.host.user.get_full_name() or self.host.user.username
            return f"Host: {name}"
        return "Unknown"

# Signal to automatically create wallet when Renter is created
@receiver(post_save, sender=Renter)
def create_renter_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(renter=instance)

# Signal to automatically create wallet when Host is created
@receiver(post_save, sender=Host)
def create_host_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(host=instance)

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('RENTAL_PAYMENT', 'Rental Payment'),
        ('RENTAL_EARNING', 'Rental Earning'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='COMPLETED')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.status}"

class GPU(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    gpu_name = models.CharField(max_length=255)
    gpu_model = models.CharField(max_length=255, blank=True, null=True)
    gpu_memory = models.PositiveSmallIntegerField()
    gpu_price = models.PositiveIntegerField()
    gpu_availability = models.BooleanField(default=True)  # is online or not
    gpu_location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        host_name = self.host.user.get_full_name() or self.host.user.username
        return f"{self.gpu_name} - {host_name}"

class Session(models.Model):
    SESSION_STATUS = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('FAILED', 'Failed'),
    ]
    
    CONNECTION_STATUS = [
        ('CONNECTING', 'Connecting'),
        ('CONNECTED', 'Connected'),
        ('DISCONNECTED', 'Disconnected'),
        ('ERROR', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gpu = models.ForeignKey(GPU, on_delete=models.CASCADE)
    renter = models.ForeignKey(Renter, on_delete=models.CASCADE)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    
    # Session timing
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='PENDING')
    
    # SSH Connection details
    ssh_host = models.CharField(max_length=255, blank=True, null=True)  # Host IP/domain
    ssh_port = models.PositiveIntegerField(default=22, blank=True, null=True)
    ssh_username = models.CharField(max_length=100, blank=True, null=True)
    ssh_password = models.CharField(max_length=255, blank=True, null=True)  # Consider encryption
    
    # Connection status and details
    connection_status = models.CharField(max_length=20, choices=CONNECTION_STATUS, default='CONNECTING')
    connection_error = models.TextField(blank=True, null=True)  # Store connection errors
    last_connected = models.DateTimeField(blank=True, null=True)  # Last successful connection time
    
    # GPU usage monitoring
    gpu_utilization = models.PositiveSmallIntegerField(default=0)  # GPU usage percentage
    memory_utilization = models.PositiveSmallIntegerField(default=0)  # Memory usage percentage
    temperature = models.PositiveSmallIntegerField(default=0)  # GPU temperature
    
    # Session management
    is_auto_reconnect = models.BooleanField(default=True)  # Auto-reconnect on disconnection
    
    # Payment
    payment_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_payment')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        renter_name = self.renter.user.get_full_name() or self.renter.user.username
        return f"Session - {self.gpu.gpu_name} - {renter_name}"
    
    @property
    def total_cost(self):
        """Calculate total cost based on session duration and GPU price"""
        if self.start_time is None:
            return 0
        if not self.end_time:
            # Session is still active, calculate cost up to now
            from django.utils import timezone
            end_time = timezone.now()
        else:
            end_time = self.end_time
        
        # Calculate duration in hours
        duration = end_time - self.start_time
        hours = duration.total_seconds() / 3600
        
        # Calculate total cost (GPU price per hour * hours)
        total_cost = self.gpu.gpu_price * hours
        return round(total_cost, 2)
    
    def process_payment(self):
        """Process payment for this session"""
        with transaction.atomic():
            total_cost = self.total_cost
            
            # Renter pays for the rental
            self.renter.pay_for_rental(
                amount=total_cost,
                description=f"Payment for {self.gpu.gpu_name} rental"
            )
            
            # Host receives the earning
            self.host.add_earning(
                amount=total_cost,
                description=f"Earning from {self.gpu.gpu_name} rental"
            )
            
            # Update session status
            self.status = 'COMPLETED'
            self.save()
            
            return total_cost
    
    def get_ssh_connection_string(self):
        """Get SSH connection string for the session"""
        if self.ssh_host and self.ssh_username:
            port = self.ssh_port or 22
            return f"ssh {self.ssh_username}@{self.ssh_host} -p {port}"
        return None
    
    def update_connection_status(self, status, error_message=None):
        """Update connection status and error message"""
        self.connection_status = status
        if error_message:
            self.connection_error = error_message
        if status == 'CONNECTED':
            from django.utils import timezone
            self.last_connected = timezone.now()
        self.save()
    
    def update_gpu_metrics(self, gpu_util, memory_util, temp):
        """Update GPU usage metrics"""
        self.gpu_utilization = gpu_util
        self.memory_utilization = memory_util
        self.temperature = temp
        self.save()
    
    def is_connected(self):
        """Check if session is currently connected"""
        return self.connection_status == 'CONNECTED'
    
    def can_reconnect(self):
        """Check if session can be reconnected"""
        return (self.status == 'ACTIVE' and 
                self.is_auto_reconnect and 
                self.connection_status in ['DISCONNECTED', 'ERROR'])
    
    def get_session_info(self):
        """Get comprehensive session information"""
        return {
            'session_id': str(self.id),
            'gpu_name': self.gpu.gpu_name,
            'renter': self.renter.user.get_full_name() or self.renter.user.username,
            'host': self.host.user.get_full_name() or self.host.user.username,
            'status': self.status,
            'connection_status': self.connection_status,
            'ssh_connection': self.get_ssh_connection_string(),
            'gpu_utilization': self.gpu_utilization,
            'memory_utilization': self.memory_utilization,
            'temperature': self.temperature,
            'total_cost': self.total_cost,
            'start_time': self.start_time,
            'end_time': self.end_time,
        }


class RelayPort(models.Model):
    """Represents a port on the relay server leased for a reverse SSH tunnel.

    The agent running on a host will open: ssh -R <port>:container_ip:22 relay@RELAY_HOST
    Renter connects via: ssh -p <port> <user>@RELAY_HOST
    """
    STATUS_CHOICES = [
        ('FREE', 'Free'),
        ('LEASED', 'Leased'),
        ('RESERVED', 'Reserved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    port = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='FREE')
    leased_to_session = models.OneToOneField('Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='relay_port')
    leased_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"RelayPort {self.port} - {self.status}"

    @classmethod
    def lease_free_port(cls, session_obj: 'Session', start_port: int, end_port: int) -> 'RelayPort':
        """Find or create a free port within the range and lease it to the session."""
        with transaction.atomic():
            # Try to find an existing FREE port in range
            free_port = (
                cls.objects.select_for_update()
                .filter(status='FREE', port__gte=start_port, port__lte=end_port)
                .order_by('port')
                .first()
            )
            if free_port is None:
                # Create a new port number by scanning the range for first unused
                used = set(
                    cls.objects.filter(port__gte=start_port, port__lte=end_port).values_list('port', flat=True)
                )
                chosen = None
                for p in range(start_port, end_port + 1):
                    if p not in used:
                        chosen = p
                        break
                if chosen is None:
                    raise ValueError("No relay ports available in the configured range")
                free_port = cls.objects.create(port=chosen, status='FREE')

            free_port.status = 'LEASED'
            free_port.leased_to_session = session_obj
            free_port.leased_at = timezone.now()
            free_port.released_at = None
            free_port.save()
            return free_port

    def release(self):
        self.status = 'FREE'
        self.released_at = timezone.now()
        self.leased_to_session = None
        self.save()

