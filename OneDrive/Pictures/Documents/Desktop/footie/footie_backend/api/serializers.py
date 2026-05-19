from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Venue, Match, PlayerBooking, Transaction, Squad, SquadMember

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # THE FIX: Added all the new Gamification fields here!
        fields = ['id', 'username', 'email', 'role', 'avatar', 'bio', 'position', 'level', 'caps', 'title']

    def get_matches_played(self, obj):
        # The Bulletproof Way: Instead of guessing the reverse link, 
        # we directly ask the PlayerBooking table to count this user's tickets!
        return PlayerBooking.objects.filter(player=obj).count()
class VenueSerializer(serializers.ModelSerializer):
    # NEW: Create a custom field to count the matches
    total_matches_hosted = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = ['id', 'name', 'location', 'pitch_size', 'price_per_hour', 'total_matches_hosted']

    def get_total_matches_hosted(self, obj):
        # Go into the Matches table and count how many belong to this specific turf
        return obj.matches.count()

class MatchSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    player_usernames = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username', source='players')

    class Meta:
        model = Match
        fields = '__all__'
        # THE FIX: Tell the serializer to stop demanding these from React!
        read_only_fields = ['creator', 'players']

    def get_creator_name(self, obj):
        return obj.creator.username if obj.creator else "Open Match"
class SquadMemberSerializer(serializers.ModelSerializer):
    # This grabs the actual text name of the user so React doesn't just get a number
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SquadMember
        fields = ['id', 'user', 'username', 'squad', 'joined_at']

class SquadSerializer(serializers.ModelSerializer):
    captain_name = serializers.CharField(source='captain.username', read_only=True)
    
    # THE MAGIC TRICK: Because we used related_name='roster' in models.py,
    # Django will automatically fetch every player on this team and package them here!
    roster = SquadMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Squad
        fields = ['id', 'name', 'captain', 'captain_name', 'created_at', 'roster']
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        # Securely hash the password before saving to SQLite
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        data['username'] = self.user.username
        data['role'] = self.user.role
        data['avatar'] = self.user.avatar
        data['title'] = self.user.title
        data['caps'] = self.user.caps
        data['position'] = self.user.position
        data['level'] = self.user.level
        data['bio'] = self.user.bio
        
        return data