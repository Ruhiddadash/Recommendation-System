# movies/serializers_rating.py
from rest_framework import serializers
from .models import UserMovieRating


class UserMovieRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMovieRating
        fields = ["movie", "rating"]
        extra_kwargs = {
            "rating": {"min_value": 1, "max_value": 5}
        }
