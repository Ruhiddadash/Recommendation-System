from django.urls import path
from .api import (
    ContentBasedRecommendView,
    MovieListView,
    RateMovieView,
    CollaborativeRecommendView,
    UserRatedSelectedMoviesView,  # <-- ADD THIS
)

urlpatterns = [
    path('recommend/content/', ContentBasedRecommendView.as_view(), name='recommend_content'),
    path('recommend/collaborative/', CollaborativeRecommendView.as_view(), name='recommend_collaborative'),
    path('all/', MovieListView.as_view(), name='movie_list'),
    path('rate/', RateMovieView.as_view(), name='movie_rate'),
    path('user-ratings/', UserRatedSelectedMoviesView.as_view(), name='user_rated_selected'),  # <-- NEW
]
