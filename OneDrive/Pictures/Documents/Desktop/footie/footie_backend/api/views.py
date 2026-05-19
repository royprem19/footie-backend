from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework_simplejwt.views import TokenObtainPairView

from django.contrib.auth import get_user_model
User = get_user_model()

from .models import Venue, Match, Transaction, PlayerBooking, Squad, SquadMember
from .serializers import (
    UserSerializer, VenueSerializer, MatchSerializer,
    SquadSerializer, RegisterSerializer, CustomTokenObtainPairSerializer
)

# --- VIEWSETS ---
class VenueViewSet(viewsets.ModelViewSet):
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all().order_by('-created_at')
    serializer_class = MatchSerializer

    def perform_create(self, serializer):
        match = serializer.save(creator=self.request.user)
        
        # THE FIX: Only charge money if it is a PRIVATE match. 
        # (Removed the rogue duplicate transaction block that was outside this if-statement!)
        if match.match_type == 'private':
            PlayerBooking.objects.create(
                player=self.request.user, 
                match=match
            )
            Transaction.objects.create(
                user=self.request.user,
                amount=match.price_inr + 15,
                transaction_type='payment',
                description=f"Payment: Pitch Booking at {match.venue.name}",
                status='completed'
            )

    def destroy(self, request, *args, **kwargs):
        match = self.get_object()
        
        Transaction.objects.create(
            user=match.creator,
            amount=match.price_inr + 15,
            transaction_type='refund',
            description=f"Refund: Cancelled booking at {match.venue.name}",
            status='completed'
        )
        
        match.status = 'cancelled'
        match.save()
        return Response({"message": "Booking successfully cancelled"}, status=status.HTTP_200_OK)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class SquadViewSet(viewsets.ModelViewSet):
    queryset = Squad.objects.all().order_by('-created_at')
    serializer_class = SquadSerializer

    def perform_create(self, serializer):
        squad = serializer.save(captain=self.request.user)
        SquadMember.objects.create(
            user=self.request.user, 
            squad=squad
        )

# --- AUTH & CUSTOM VIEWS ---

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_match(request, pk):
    try:
        match = Match.objects.get(pk=pk)
        
        if request.user in match.players.all():
            return Response({"error": "You are already booked for this match!"}, status=400)

        if match.filled_slots >= match.total_slots:
            return Response({"error": "Match is completely full!"}, status=400)

        match.players.add(request.user)
        match.filled_slots += 1
        match.save()
        
        total_paid = match.price_inr + 15
        
        Transaction.objects.create(
            user=request.user,
            amount=total_paid,
            transaction_type='payment',
            description=f"Pitch Booking: {match.venue_name if hasattr(match, 'venue_name') else 'Premium Turf'}",
            status='completed'
        )
        
        return Response({"message": "Successfully joined the match!"})
        
    except Match.DoesNotExist:
        return Response({"error": "Match not found"}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_match(request, pk):
    try:
        match = Match.objects.get(pk=pk)
        
        if request.user in match.players.all():
            match.players.remove(request.user)
            match.filled_slots -= 1
            match.save()
            
            # THE FIX: Add the ₹15 platform fee back to their refund!
            total_refund = match.price_inr + 15
            
            Transaction.objects.create(
                user=request.user,
                amount=total_refund,
                transaction_type='refund',
                description=f"Refund: Left Open Match at {match.venue_name if hasattr(match, 'venue_name') else 'Premium Turf'}",
                status='completed'
            )
            return Response({"message": "Successfully left the match and refunded!"}, status=200)
        else:
            return Response({"error": "You are not in this match roster!"}, status=400)
            
    except Match.DoesNotExist:
        return Response({"error": "Match not found"}, status=404)