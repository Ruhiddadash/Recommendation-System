from django.urls import path
from .api import ContentBasedRecommendView, MovieListView  # keep existing views

urlpatterns = [
    path('recommend/content/', ContentBasedRecommendView.as_view(), name='recommend_content'),
    #path('recommend/collaborative/', CollaborativeRecommendView.as_view(), name='recommend_collaborative'),
    path('all/', MovieListView.as_view(), name='movie_list'),
]
