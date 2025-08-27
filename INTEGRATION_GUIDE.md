# Labhya Compute - Frontend-Backend Integration Guide

## Overview

This guide covers the complete integration between the React TypeScript frontend and Django REST API backend for the Labhya Compute GPU renting platform.

## Quick Start

1. **Start Backend**: `cd backend && python manage.py runserver`
2. **Start Frontend**: `cd frontend && npm run dev`
3. **Test Integration**: `cd frontend && npm run test:integration`

## API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Token refresh
- `POST /api/auth/register/host/` - Host registration
- `POST /api/auth/register/renter/` - Renter registration

### Core Features
- `GET /api/gpus/available/` - List available GPUs
- `GET /api/sessions/` - List sessions
- `GET /api/wallets/` - Wallet information
- `GET /api/dashboard/stats/` - Dashboard statistics

## Integration Status

✅ **Backend**: Django REST API with JWT authentication
✅ **Frontend**: React TypeScript with Zustand state management
✅ **CORS**: Properly configured for cross-origin requests
✅ **Authentication**: JWT token management with auto-refresh
✅ **Type Safety**: TypeScript interfaces matching backend models
✅ **Error Handling**: Comprehensive error handling and user feedback

## Next Steps

1. Test the integration using the provided test script
2. Start both servers and verify connectivity
3. Test authentication flow
4. Verify GPU and session management
5. Check wallet and transaction functionality

The frontend is now fully integrated with the Django backend and ready for development and testing.
