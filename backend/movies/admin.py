from django.contrib import admin
from .models import Movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "genres", "year")
    search_fields = ("title", "genres")

from .models import UserMovieRating

@admin.register(UserMovieRating)
class UserMovieRatingAdmin(admin.ModelAdmin):
    list_display = ("user", "movie", "rating", "updated_at")
    list_filter = ("rating", "updated_at")
    search_fields = ("user__username", "movie__title")