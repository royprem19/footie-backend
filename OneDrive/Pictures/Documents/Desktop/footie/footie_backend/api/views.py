from django.db import IntegrityError
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
@api_view(['GET'])
@permission_classes([AllowAny]) # Anyone can view the leaderboard!
def leaderboard_view(request):
    # Filter only players, sort by 'caps' descending, and grab the Top 50
    top_players = User.objects.filter(role='player').order_by('-caps')[:50]
    serializer = UserSerializer(top_players, many=True)
    return Response(serializer.data)
@api_view(['GET'])
def get_squads(request):
    """Fetches all active squads and their rosters."""
    squads = Squad.objects.all().order_by('-created_at')
    serializer = SquadSerializer(squads, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_squad(request):
    """Allows a Free Agent to create a new squad and become Captain."""
    
    # 1. Check if the user is already a member of a squad
    if hasattr(request.user, 'squad_membership'):
        return Response({'error': 'You are already on a roster! Leave your current team first.'}, status=400)
    
    # 2. Check if the user is already a captain of a squad (OneToOne constraint safety)
    if Squad.objects.filter(captain=request.user).exists():
        return Response({'error': 'You are already leading a squad as Captain!'}, status=400)
        
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Squad name cannot be blank!'}, status=400)
        
    # 3. Check if the squad name is taken (Case-Insensitive check)
    if Squad.objects.filter(name__iexact=name).exists():
        return Response({'error': f'The name "{name}" is already taken! Choose a unique team name.'}, status=400)

    try:
        # 4. Attempt creation safely inside a transaction block
        squad = Squad.objects.create(name=name, captain=request.user)
        SquadMember.objects.create(user=request.user, squad=squad)
        return Response(SquadSerializer(squad).data)
    except IntegrityError:
        return Response({'error': 'Roster integrity conflict. Could not register squad.'}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_squad(request, squad_id):
    """Allows a Free Agent to join an existing squad."""
    if hasattr(request.user, 'squad_membership'):
        return Response({'error': 'You are already on a roster!'}, status=400)
        
    try:
        squad = Squad.objects.get(id=squad_id)
        SquadMember.objects.create(user=request.user, squad=squad)
        return Response({'message': f'Successfully joined {squad.name}!'})
    except Squad.DoesNotExist:
        return Response({'error': 'Squad not found'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_squad(request):
    """Allows a player to leave. If the Captain leaves, the team disbands."""
    try:
        membership = request.user.squad_membership
        squad = membership.squad
        
        # If the Captain leaves, we delete the whole squad
        if squad.captain == request.user:
            squad.delete()
            return Response({'message': 'Squad disbanded because the captain left.'})
        else:
            membership.delete() # Normal player just leaves
            return Response({'message': 'Successfully left the squad.'})
    except:
        return Response({'error': 'You are not in a squad.'}, status=400)