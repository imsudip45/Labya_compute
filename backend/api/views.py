from django.shortcuts import render
from django.db import models

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Renter, Host, Wallet, Transaction, GPU, Session
from .serializers import (
    RenterSerializer, RenterDetailSerializer, RenterWalletSerializer,
    HostSerializer, HostDetailSerializer, HostWalletSerializer,
    WalletSerializer, WalletDetailSerializer, WalletTransactionSerializer,
    TransactionSerializer,
    GPUSerializer,
    SessionSerializer, SessionDetailSerializer, SessionCreateSerializer, SessionUpdateSerializer
)


class RegisterRenterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        password = request.data.get('password')
        if not all([name, email, password]):
            return Response({'error': 'name, email, password required'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=email).exists():
            return Response({'error': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
            renter = Renter.objects.create(user=user)
            # Wallet auto-created via signals
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Renter registered',
                'renter_id': str(renter.id),
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)


class RegisterHostView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        password = request.data.get('password')
        if not all([name, email, password]):
            return Response({'error': 'name, email, password required'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=email).exists():
            return Response({'error': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
            host = Host.objects.create(user=user)
            # Wallet auto-created via signals
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Host registered',
                'host_id': str(host.id),
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)


class RenterViewSet(viewsets.ModelViewSet):
    queryset = Renter.objects.all()
    serializer_class = RenterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RenterDetailSerializer
        return RenterSerializer

    @action(detail=True, methods=['post'])
    def add_money(self, request, pk=None):
        """Add money to renter's wallet"""
        renter = self.get_object()
        amount = request.data.get('amount')
        description = request.data.get('description', 'Deposit')

        try:
            amount = float(amount)
        except Exception:
            amount = None
        if not amount or amount <= 0:
            return Response(
                {'error': 'Valid amount is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_balance = renter.add_money(amount, description)
            return Response({
                'message': 'Money added successfully',
                'new_balance': new_balance,
                'amount_added': amount
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def wallet(self, request, pk=None):
        """Get renter's wallet details"""
        renter = self.get_object()
        wallet = renter.get_wallet()
        serializer = WalletDetailSerializer(wallet)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get all sessions for this renter"""
        renter = self.get_object()
        sessions = Session.objects.filter(renter=renter)
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)


class HostViewSet(viewsets.ModelViewSet):
    queryset = Host.objects.all()
    serializer_class = HostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HostDetailSerializer
        return HostSerializer

    @action(detail=True, methods=['post'])
    def withdraw_money(self, request, pk=None):
        """Withdraw money from host's wallet"""
        host = self.get_object()
        amount = request.data.get('amount')
        description = request.data.get('description', 'Withdrawal')

        try:
            amount = float(amount)
        except Exception:
            amount = None
        if not amount or amount <= 0:
            return Response(
                {'error': 'Valid amount is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_balance = host.withdraw_money(amount, description)
            return Response({
                'message': 'Money withdrawn successfully',
                'new_balance': new_balance,
                'amount_withdrawn': amount
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def wallet(self, request, pk=None):
        """Get host's wallet details"""
        host = self.get_object()
        wallet = host.get_wallet()
        serializer = WalletDetailSerializer(wallet)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def gpus(self, request, pk=None):
        """Get all GPUs for this host"""
        host = self.get_object()
        gpus = GPU.objects.filter(host=host)
        serializer = GPUSerializer(gpus, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get all sessions for this host"""
        host = self.get_object()
        sessions = Session.objects.filter(host=host)
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WalletDetailSerializer
        return WalletSerializer

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get all transactions for this wallet"""
        wallet = self.get_object()
        transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Transaction.objects.all().order_by('-created_at')
        wallet_id = self.request.query_params.get('wallet', None)
        transaction_type = self.request.query_params.get('type', None)
        
        if wallet_id:
            queryset = queryset.filter(wallet_id=wallet_id)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset


class GPUViewSet(viewsets.ModelViewSet):
    queryset = GPU.objects.all()
    serializer_class = GPUSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = GPU.objects.all()
        host_id = self.request.query_params.get('host', None)
        available_only = self.request.query_params.get('available', None)
        
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        if available_only == 'true':
            queryset = queryset.filter(gpu_availability=True)
            
        return queryset

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle GPU availability"""
        gpu = self.get_object()
        gpu.gpu_availability = not gpu.gpu_availability
        gpu.save()
        
        return Response({
            'message': f'GPU availability set to {gpu.gpu_availability}',
            'gpu_availability': gpu.gpu_availability
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get all sessions for this GPU"""
        gpu = self.get_object()
        sessions = Session.objects.filter(gpu=gpu)
        serializer = SessionSerializer(sessions, many=True)
        return Response(serializer.data)


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all().order_by('-created_at')
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SessionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SessionUpdateSerializer
        elif self.action == 'retrieve':
            return SessionDetailSerializer
        return SessionSerializer

    def get_queryset(self):
        queryset = Session.objects.all().order_by('-created_at')
        renter_id = self.request.query_params.get('renter', None)
        host_id = self.request.query_params.get('host', None)
        gpu_id = self.request.query_params.get('gpu', None)
        status_filter = self.request.query_params.get('status', None)
        
        if renter_id:
            queryset = queryset.filter(renter_id=renter_id)
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        if gpu_id:
            queryset = queryset.filter(gpu_id=gpu_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset

    def create(self, request, *args, **kwargs):
        """Create a new session with validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            session = serializer.save()
            
            # Mark GPU as unavailable
            session.gpu.gpu_availability = False
            session.gpu.save()
            
            # Update session status to ACTIVE
            session.status = 'ACTIVE'
            session.save()
            
        return Response(
            SessionDetailSerializer(session).data, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End a session and process payment"""
        session = self.get_object()
        
        if session.status == 'COMPLETED':
            return Response(
                {'error': 'Session is already completed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Set end time
                session.end_time = timezone.now()
                session.status = 'COMPLETED'
                session.save()
                
                # Process payment
                total_cost = session.process_payment()
                
                # Mark GPU as available again
                session.gpu.gpu_availability = True
                session.gpu.save()
                
            return Response({
                'message': 'Session ended successfully',
                'total_cost': total_cost,
                'session_id': str(session.id)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def update_connection_status(self, request, pk=None):
        """Update session connection status"""
        session = self.get_object()
        status_val = request.data.get('status')
        error_message = request.data.get('error_message')
        
        if not status_val:
            return Response(
                {'error': 'Status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session.update_connection_status(status_val, error_message)
            return Response({
                'message': 'Connection status updated',
                'connection_status': session.connection_status
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def update_gpu_metrics(self, request, pk=None):
        """Update GPU usage metrics"""
        session = self.get_object()
        gpu_util = request.data.get('gpu_utilization', 0)
        memory_util = request.data.get('memory_utilization', 0)
        temperature = request.data.get('temperature', 0)
        
        try:
            session.update_gpu_metrics(gpu_util, memory_util, temperature)
            return Response({
                'message': 'GPU metrics updated',
                'gpu_utilization': session.gpu_utilization,
                'memory_utilization': session.memory_utilization,
                'temperature': session.temperature
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def connection_info(self, request, pk=None):
        """Get SSH connection information"""
        session = self.get_object()
        return Response({
            'ssh_connection_string': session.get_ssh_connection_string(),
            'ssh_host': session.ssh_host,
            'ssh_port': session.ssh_port,
            'ssh_username': session.ssh_username,
            'connection_status': session.connection_status,
            'is_connected': session.is_connected()
        })

    @action(detail=True, methods=['post'])
    def cancel_session(self, request, pk=None):
        """Cancel an active session"""
        session = self.get_object()
        
        if session.status != 'ACTIVE':
            return Response(
                {'error': 'Only active sessions can be cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                session.status = 'CANCELLED'
                session.end_time = timezone.now()
                session.save()
                
                # Mark GPU as available again
                session.gpu.gpu_availability = True
                session.gpu.save()
                
            return Response({
                'message': 'Session cancelled successfully',
                'session_id': str(session.id)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


# Additional utility views
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get dashboard statistics"""
        total_renters = Renter.objects.count()
        total_hosts = Host.objects.count()
        total_gpus = GPU.objects.count()
        available_gpus = GPU.objects.filter(gpu_availability=True).count()
        active_sessions = Session.objects.filter(status='ACTIVE').count()
        total_transactions = Transaction.objects.count()
        
        # Calculate total revenue (all rental earnings)
        total_revenue = Transaction.objects.filter(
            transaction_type='RENTAL_EARNING'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        return Response({
            'total_renters': total_renters,
            'total_hosts': total_hosts,
            'total_gpus': total_gpus,
            'available_gpus': available_gpus,
            'active_sessions': active_sessions,
            'total_transactions': total_transactions,
            'total_revenue': total_revenue
        })


class AvailableGPUsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all available GPUs for rent"""
        gpus = GPU.objects.filter(gpu_availability=True)
        serializer = GPUSerializer(gpus, many=True)
        return Response(serializer.data)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Accept 'email' and map it to 'username' expected by default User model
        email = attrs.pop('email', None)
        if email is not None and 'username' not in attrs:
            attrs['username'] = email
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
