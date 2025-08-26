from django.contrib import admin
from .models import Renter, Host, Wallet, Transaction, GPU, Session

# Register your models here.

@admin.register(Renter)
class RenterAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_email', 'id')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'user__username')
    list_filter = ('user__date_joined',)
    ordering = ('user__first_name',)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

@admin.register(Host)
class HostAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_email', 'id')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'user__username')
    list_filter = ('user__date_joined',)
    ordering = ('user__first_name',)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_name.short_description = 'Name'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('get_owner_name', 'balance', 'currency', 'created_at')
    search_fields = ('renter__user__first_name', 'renter__user__last_name', 'renter__user__email', 'host__user__first_name', 'host__user__last_name', 'host__user__email')
    list_filter = ('currency', 'created_at')
    ordering = ('-created_at',)
    
    def get_owner_name(self, obj):
        if obj.renter:
            name = obj.renter.user.get_full_name() or obj.renter.user.username
            return f"Renter: {name}"
        elif obj.host:
            name = obj.host.user.get_full_name() or obj.host.user.username
            return f"Host: {name}"
        return "Unknown"
    get_owner_name.short_description = 'Owner'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'amount', 'get_wallet_owner', 'status', 'created_at')
    search_fields = ('wallet__renter__user__first_name', 'wallet__renter__user__last_name', 'wallet__host__user__first_name', 'wallet__host__user__last_name', 'description')
    list_filter = ('transaction_type', 'status', 'created_at')
    ordering = ('-created_at',)
    
    def get_wallet_owner(self, obj):
        if obj.wallet.renter:
            name = obj.wallet.renter.user.get_full_name() or obj.wallet.renter.user.username
            return f"Renter: {name}"
        elif obj.wallet.host:
            name = obj.wallet.host.user.get_full_name() or obj.wallet.host.user.username
            return f"Host: {name}"
        return "Unknown"
    get_wallet_owner.short_description = 'Wallet Owner'

@admin.register(GPU)
class GPUAdmin(admin.ModelAdmin):
    list_display = ('gpu_name', 'host', 'gpu_memory', 'gpu_price', 'gpu_availability', 'gpu_location')
    search_fields = ('gpu_name', 'host__user__first_name', 'host__user__last_name', 'host__user__email', 'gpu_location')
    list_filter = ('gpu_availability', 'gpu_memory', 'created_at')
    ordering = ('-created_at',)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('gpu', 'renter', 'host', 'start_time', 'end_time', 'status', 'connection_status', 'get_total_cost')
    search_fields = ('gpu__gpu_name', 'renter__user__first_name', 'renter__user__last_name', 'host__user__first_name', 'host__user__last_name', 'ssh_host', 'ssh_username')
    list_filter = ('status', 'connection_status', 'start_time', 'created_at')
    ordering = ('-start_time',)
    
    fieldsets = (
        ('Session Information', {
            'fields': ('gpu', 'renter', 'host', 'start_time', 'end_time', 'status')
        }),
        ('SSH Connection', {
            'fields': ('ssh_host', 'ssh_port', 'ssh_username', 'ssh_password')
        }),
        ('Connection Status', {
            'fields': ('connection_status', 'connection_error', 'last_connected')
        }),
        ('GPU Monitoring', {
            'fields': ('gpu_utilization', 'memory_utilization', 'temperature')
        }),
        ('Session Management', {
            'fields': ('is_auto_reconnect', 'payment_transaction')
        }),
    )
    
    readonly_fields = ('get_ssh_connection_string', 'get_total_cost', 'last_connected')
    
    def get_ssh_connection_string(self, obj):
        return obj.get_ssh_connection_string() or "Not configured"
    get_ssh_connection_string.short_description = 'SSH Connection String'
    
    def get_total_cost(self, obj):
        return f"NPR {obj.total_cost}"
    get_total_cost.short_description = 'Total Cost'

admin.site.site_header = "Labhya Compute Admin"
admin.site.site_title = "Labhya Compute Admin Portal"
admin.site.index_title = "Welcome to Labhya Compute Admin Portal"