from django.db import models
from django.contrib.auth.models import User


class Movie(models.Model):
    movieId = models.IntegerField(null=True, blank=True)  # MovieLens id
    title = models.CharField(max_length=255)
    genres = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    director = models.CharField(max_length=255, null=True, blank=True)
    actors = models.CharField(max_length=500, null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.title

class UserMovieRating(models.Model):
    """
    Stores 1-5 user ratings for movies.
    Unique(user, movie) so user can change rating but not duplicate.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="movie_ratings")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="ratings")
    rating = models.PositiveIntegerField()  # 1..5

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "movie")

    def __str__(self):
        return f"{self.user.username} → {self.movie.title}: {self.rating}"