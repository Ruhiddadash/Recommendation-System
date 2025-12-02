from django.db import models

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
