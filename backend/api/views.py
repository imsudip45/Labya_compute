from django.shortcuts import render
from django.db import models
from django.utils import timezone

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

from .models import Renter, Host, Wallet, Transaction, GPU, Session, RelayPort
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

    def list(self, request, *args, **kwargs):
        """Get current user's renter profile"""
        user = request.user
        
        try:
            renter = Renter.objects.get(user=user)
            serializer = RenterDetailSerializer(renter)
            return Response(serializer.data)
        except Renter.DoesNotExist:
            return Response(
                {'error': 'User is not a renter'}, 
                status=status.HTTP_404_NOT_FOUND
            )

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

    def list(self, request, *args, **kwargs):
        """Get current user's host profile"""
        user = request.user
        
        try:
            host = Host.objects.get(user=user)
            serializer = HostDetailSerializer(host)
            return Response(serializer.data)
        except Host.DoesNotExist:
            return Response(
                {'error': 'User is not a host'}, 
                status=status.HTTP_404_NOT_FOUND
            )

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

    def list(self, request, *args, **kwargs):
        """Get current user's wallet"""
        user = request.user
        
        # Try to find user's wallet
        try:
            host = Host.objects.get(user=user)
            wallet = host.get_wallet()
        except Host.DoesNotExist:
            try:
                renter = Renter.objects.get(user=user)
                wallet = renter.get_wallet()
            except Renter.DoesNotExist:
                return Response(
                    {'error': 'No wallet found for user'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        serializer = WalletDetailSerializer(wallet)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_funds(self, request):
        """Add funds to current user's wallet"""
        user = request.user
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
            # Try renter first
            renter = Renter.objects.get(user=user)
            new_balance = renter.add_money(amount, description)
            return Response({
                'message': 'Funds added successfully',
                'new_balance': new_balance,
                'amount_added': amount
            }, status=status.HTTP_200_OK)
        except Renter.DoesNotExist:
            return Response(
                {'error': 'Only renters can add funds'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def withdraw_funds(self, request):
        """Withdraw funds from current user's wallet (hosts only)"""
        user = request.user
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
            # Try host first
            host = Host.objects.get(user=user)
            new_balance = host.withdraw_money(amount, description)
            return Response({
                'message': 'Funds withdrawn successfully',
                'new_balance': new_balance,
                'amount_withdrawn': amount
            }, status=status.HTTP_200_OK)
        except Host.DoesNotExist:
            return Response(
                {'error': 'Only hosts can withdraw funds'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

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
        user = self.request.user
        
        # Get user's wallet
        try:
            host = Host.objects.get(user=user)
            wallet = host.get_wallet()
        except Host.DoesNotExist:
            try:
                renter = Renter.objects.get(user=user)
                wallet = renter.get_wallet()
            except Renter.DoesNotExist:
                return Transaction.objects.none()
        
        queryset = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
        transaction_type = self.request.query_params.get('type', None)
        
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
            
        return queryset


class GPUViewSet(viewsets.ModelViewSet):
    queryset = GPU.objects.all()
    serializer_class = GPUSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = GPU.objects.all()
        user = self.request.user
        
        # If user is a host, show only their GPUs by default
        try:
            host = Host.objects.get(user=user)
            queryset = queryset.filter(host=host)
        except Host.DoesNotExist:
            # If user is not a host, show all GPUs (for renters)
            pass
        
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
        user = self.request.user
        
        # Filter by current user's role
        try:
            host = Host.objects.get(user=user)
            queryset = queryset.filter(host=host)
        except Host.DoesNotExist:
            try:
                renter = Renter.objects.get(user=user)
                queryset = queryset.filter(renter=renter)
            except Renter.DoesNotExist:
                # User has no role, return empty queryset
                return Session.objects.none()
        
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
        """Create a new session as PENDING from gpu id only; allocate relay info; GPU unavailable.
        start_time will be set by agent when ready.
        """
        # Expect payload: { "gpu": <gpu_uuid> }
        gpu_id = request.data.get('gpu')
        if not gpu_id:
            return Response({'error': 'gpu field is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            gpu = GPU.objects.get(id=gpu_id)
        except GPU.DoesNotExist:
            return Response({'error': 'GPU not found'}, status=status.HTTP_404_NOT_FOUND)

        # Determine renter from current user
        try:
            renter = Renter.objects.get(user=request.user)
        except Renter.DoesNotExist:
            return Response({'error': 'Only renters can create sessions'}, status=status.HTTP_403_FORBIDDEN)

        # Validate availability and balance
        if not gpu.gpu_availability:
            return Response({'error': 'GPU is not available for rent'}, status=status.HTTP_400_BAD_REQUEST)
        wallet = renter.get_wallet()
        if wallet.balance < gpu.gpu_price:
            return Response({'error': 'Insufficient balance to rent this GPU'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Create session object
            session = Session.objects.create(
                gpu=gpu,
                renter=renter,
                host=gpu.host,
                status='PENDING',
            )

            # Allocate a relay port for reverse SSH
            from django.conf import settings
            relay_host = getattr(settings, 'RELAY_HOST', 'localhost')
            port_range = getattr(settings, 'RELAY_PORT_RANGE', (8001, 8999))
            start_port, end_port = port_range

            # Lock and lease a port
            leased = RelayPort.lease_free_port(session, start_port, end_port)

            # Set SSH connection info for renter
            session.ssh_host = relay_host
            session.ssh_port = leased.port
            session.ssh_username = f"sess_{str(session.id)[:8]}"

            # Mark GPU as unavailable and leave session pending until agent starts container
            session.gpu.gpu_availability = False
            session.gpu.save()
            session.save()
            
        return Response(
            SessionDetailSerializer(session).data, 
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def mark_started(self, request, pk=None):
        """Called by host agent when container is ready and reverse SSH is up.
        Sets start_time and marks session ACTIVE.
        Optionally accepts ssh_password for renter convenience.
        Can also accept ssh_host and ssh_port overrides from agent for direct connection fallback.
        """
        session = self.get_object()
        if session.status not in ['PENDING', 'ACTIVE']:
            return Response({'error': 'Invalid session state'}, status=status.HTTP_400_BAD_REQUEST)
        ssh_password = request.data.get('ssh_password')
        ssh_host = request.data.get('ssh_host')
        ssh_port = request.data.get('ssh_port')
        ssh_username = request.data.get('ssh_username')
        with transaction.atomic():
            from django.utils import timezone
            if session.start_time is None:
                session.start_time = timezone.now()
            session.status = 'ACTIVE'
            if ssh_password:
                session.ssh_password = ssh_password
            if ssh_host:
                session.ssh_host = ssh_host
            if ssh_port:
                try:
                    session.ssh_port = int(ssh_port)
                except Exception:
                    pass
            if ssh_username:
                session.ssh_username = ssh_username
            session.connection_status = 'CONNECTED'
            session.last_connected = timezone.now()
            session.save()
        return Response({'message': 'Session marked as started', 'session_id': str(session.id)}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def pending_for_host(self, request):
        """Agent endpoint: list PENDING sessions for the authenticated host with relay info."""
        user = request.user
        try:
            host = Host.objects.get(user=user)
        except Host.DoesNotExist:
            return Response({'error': 'Only hosts can query pending sessions'}, status=status.HTTP_403_FORBIDDEN)
        sessions = Session.objects.filter(host=host, status='PENDING').order_by('created_at')
        data = SessionSerializer(sessions, many=True).data
        return Response(data)

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

                # Release relay port if leased
                try:
                    if hasattr(session, 'relay_port') and session.relay_port:
                        session.relay_port.release()
                except Exception:
                    pass
                
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

                # Release relay port if leased
                try:
                    if hasattr(session, 'relay_port') and session.relay_port:
                        session.relay_port.release()
                except Exception:
                    pass
                
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
        user = request.user
        
        # Determine if user is host or renter
        try:
            host = Host.objects.get(user=user)
            is_host = True
        except Host.DoesNotExist:
            is_host = False
            
        try:
            renter = Renter.objects.get(user=user)
            is_renter = True
        except Renter.DoesNotExist:
            is_renter = False
        
        if is_host:
            # Host dashboard stats
            my_gpus = GPU.objects.filter(host=host)
            total_gpus = my_gpus.count()
            available_gpus = my_gpus.filter(gpu_availability=True).count()
            active_sessions = Session.objects.filter(gpu__host=host, status='ACTIVE').count()
            
            # Calculate today's earnings
            today = timezone.now().date()
            todays_earnings = Transaction.objects.filter(
                wallet__host=host,
                transaction_type='RENTAL_EARNING',
                created_at__date=today
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            return Response({
                'totalGPUs': total_gpus,
                'activeSessions': active_sessions,
                'todaysEarnings': todays_earnings,
                'availableGPUs': available_gpus
            })
            
        elif is_renter:
            # Renter dashboard stats
            my_sessions = Session.objects.filter(renter=renter)
            total_sessions = my_sessions.count()
            active_sessions = my_sessions.filter(status='ACTIVE').count()
            
            # Calculate total spent
            total_spent = Transaction.objects.filter(
                wallet__renter=renter,
                transaction_type='PAYMENT'
            ).aggregate(total=models.Sum('amount'))['total'] or 0
            
            return Response({
                'totalSessions': total_sessions,
                'activeSessions': active_sessions,
                'totalSpent': abs(total_spent)  # Make positive for display
            })
        
        else:
            # Fallback for users without role
            return Response({
                'totalGPUs': 0,
                'activeSessions': 0,
                'todaysEarnings': 0,
                'totalSessions': 0,
                'totalSpent': 0
            })


class AvailableGPUsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get all available GPUs for rent"""
        gpus = GPU.objects.filter(gpu_availability=True)
        serializer = GPUSerializer(gpus, many=True)
        return Response(serializer.data)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace username field with email field
        if 'username' in self.fields:
            self.fields['email'] = self.fields.pop('username')
    
    def validate(self, attrs):
        # Map email to username for authentication
        if 'email' in attrs:
            attrs['username'] = attrs.pop('email')
        return super().validate(attrs)


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
