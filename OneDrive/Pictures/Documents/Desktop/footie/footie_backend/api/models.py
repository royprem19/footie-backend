from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = (
        ('player', 'Player'),
        ('admin', 'Turf Manager'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='player')
    
    # --- NEW: GAMIFICATION & PROFILE FIELDS ---
    avatar = models.CharField(max_length=255, default='⚽')
    bio = models.TextField(default='Ready to play!', blank=True)
    position = models.CharField(max_length=50, default='Striker')
    level = models.CharField(max_length=50, default='Intermediate')
    
    # Leaderboard Stats
    caps = models.IntegerField(default=0) # Total matches played
    title = models.CharField(max_length=50, default='Rookie')

    def __str__(self):
        return f"{self.username} ({self.role} - {self.title})"

# 2. Venues Table
class Venue(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='venues')
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    pitch_size = models.CharField(max_length=50) 
    price_per_hour = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.location}"

# 3. Matches Table (The Booking Engine)
class Match(models.Model):
    MATCH_TYPES = (
        ('private', 'Private Custom Booking'),
        ('open', 'Open Play Session'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='matches')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_matches')
    match_type = models.CharField(max_length=10, choices=MATCH_TYPES, default='private')
    
    
    # Add this line to hold all the players who book this match!
    players = models.ManyToManyField(User, related_name='joined_matches', blank=True)
    
    date = models.DateField()
    time_slots = models.JSONField(default=list) 
    total_slots = models.IntegerField(default=10)
    filled_slots = models.IntegerField(default=0)
    price_inr = models.IntegerField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.venue.name} | {self.date} ({self.match_type})"

# 4. The Roster (Tickets)
class PlayerBooking(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='roster')
    player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_bookings')
    payment_status = models.CharField(max_length=20, default='paid')
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('match', 'player')

    def __str__(self):
        return f"{self.player.username} -> {self.match.venue.name}"
# 5. The Financial Ledger
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('payment', 'Pitch Booking Payment'),
        ('refund', 'Booking Refund'), # <--- NEW: Add this line!
        ('withdrawal', 'Bank Withdrawal'),
    )
    STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('processing', 'Processing'),
        ('failed', 'Failed'),
    )

    # Who does this money belong to?
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    
    # E.g., "HDFC Bank ending in 4021" or "Booking at Kickoff Arena"
    description = models.CharField(max_length=255) 
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='completed')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.transaction_type} | ₹{self.amount}"
# ==========================================
# PHASE 3: SQUADS & TEAMS
# ==========================================

class Squad(models.Model):
    name = models.CharField(max_length=50, unique=True)
    # The captain is the boss. A user can only captain ONE squad at a time.
    captain = models.OneToOneField(User, on_delete=models.CASCADE, related_name='captained_squad')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SquadMember(models.Model):
    # This OneToOneField is the magic lock. It ensures a player can only be in this table ONCE.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='squad_membership')
    
    # But a Squad can have MANY players linked to it!
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='roster')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} -> {self.squad.name}"