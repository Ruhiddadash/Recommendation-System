from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from movies.services.content_based import ContentBasedRecommender
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import RecommendationRequestSerializer, MovieRecommendationSerializer
from movies.models import Movie

from django.db.models import Count
import random

from rest_framework import status
from movies.recommender.contentbase import recommend_content_based
#from movies.recommender.collabfiltering import recommend_collaborative

    
class MovieListView(APIView):
    def get(self, request):
        movies = list(Movie.objects.all().values("id", "title", "genres", "year"))
        return Response(movies)
    


class ContentBasedRecommendView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RecommendationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        selected_ids = serializer.validated_data['selected_ids']
        top_k = serializer.validated_data.get('top_k', 16)

        # Call your content-based recommender function
        # It should return a list of dicts: [{'id':..., 'title':..., 'genres':..., 'score':...}, ...]
        try:
            recs = recommend_content_based(selected_ids, top_k=top_k, user=request.user)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        out = MovieRecommendationSerializer(recs, many=True)
        print(out.data)
        return Response(out.data, status=status.HTTP_200_OK)


# class CollaborativeRecommendView(APIView):
#     authentication_classes = [JWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = RecommendationRequestSerializer(data=request.data)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#         selected_ids = serializer.validated_data['selected_ids']
#         top_k = serializer.validated_data.get('top_k', 16)

#         try:
#             recs = recommend_collaborative(selected_ids, top_k=top_k, user=request.user)
#         except Exception as e:
#             return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         out = MovieRecommendationSerializer(recs, many=True)
#         return Response(out.data, status=status.HTTP_200_OK)