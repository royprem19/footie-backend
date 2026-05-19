from .models import Venue, Match, PlayerBooking, Transaction, Squad, SquadMember
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Venue, Match, PlayerBooking

# 1. Register our custom User
admin.site.register(User, UserAdmin)
admin.site.register(Transaction)
admin.site.register(Squad)
admin.site.register(SquadMember)

# 2. Register the Venues so you can add them
@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'pitch_size', 'price_per_hour')
    search_fields = ('name', 'location')

# 3. Register the Matches
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('venue', 'date', 'match_type', 'filled_slots', 'total_slots', 'status')
    list_filter = ('status', 'match_type', 'date')

# 4. Register the Tickets/Rosters
@admin.register(PlayerBooking)
class PlayerBookingAdmin(admin.ModelAdmin):
    list_display = ('player', 'match', 'payment_status', 'booked_at')