from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status

from movies.models import Movie, UserMovieRating

from .serializers import RecommendationRequestSerializer, MovieRecommendationSerializer
from .serializers_rating import UserMovieRatingSerializer
from movies.recommender.contentbase import recommend_content_based
from movies.recommender.collabfiltering import recommend_collaborative


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

        selected_ids = serializer.validated_data["selected_ids"]
        top_k = serializer.validated_data.get("top_k", 16)

        try:
            recs = recommend_content_based(
                selected_ids,
                top_k=top_k,
                user=request.user
            )
        except Exception as e:
            # Return JSON error rather than HTML traceback
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # NOTE: your content-based recommendations are simple:
        #   [{"id":..,"title":..,"genres":..,"score":..}, ...]
        # If you created a dedicated serializer (recommended), you can
        # serialize here. For now we just return the list as-is.
        return Response(recs, status=status.HTTP_200_OK)


class CollaborativeRecommendView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Collaborative Filtering endpoint.

        Rules:
        - User must have rated at least one of the *currently selected movies*.
          Otherwise we return a 400 with a clear message.
        - CF then runs using all historical ratings, but similarity is boosted
          for neighbors who agree on the selected movies (see collabfiltering.py).
        """
        serializer = RecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        selected_ids = serializer.validated_data["selected_ids"]
        top_k = serializer.validated_data.get("top_k", 16)
        user = request.user

        # --- Enforce: must rate at least one of the selected movies ---
        rated_selected_count = UserMovieRating.objects.filter(
            user=user,
            movie_id__in=selected_ids,
        ).count()

        if rated_selected_count == 0:
            return Response(
                {
                    "detail": (
                        "To use collaborative filtering, please rate at least "
                        "one of the movies you selected."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            recs = recommend_collaborative(
                selected_ids,
                top_k=top_k,
                user=user,
            )
        except ValueError as e:
            # Typical CF errors: not enough ratings overall, no neighbors, etc.
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Unexpected internal error
            return Response(
                {"detail": f"Unexpected error while running CF: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        output = MovieRecommendationSerializer(recs, many=True)
        return Response(output.data, status=status.HTTP_200_OK)


class RateMovieView(APIView):
    """
    Save or update a 1–5 rating for a movie by the current user.

    Expected JSON:
    {
        "movie": 23,
        "rating": 4
    }
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserMovieRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # For a ModelSerializer "movie" is already a Movie instance
        movie = serializer.validated_data["movie"]
        rating = serializer.validated_data["rating"]

        # Upsert rating (one per user+movie)
        rating_obj, created = UserMovieRating.objects.update_or_create(
            user=request.user,
            movie=movie,
            defaults={"rating": rating},
        )

        return Response(
            {
                "success": True,
                "created": created,
                "movie_id": movie.id,
                "rating": rating_obj.rating,
            },
            status=status.HTTP_200_OK,
        )

class UserRatedSelectedMoviesView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        selected_ids = request.data.get("selected_ids", [])
        if not isinstance(selected_ids, list) or len(selected_ids) == 0:
            return Response(
                {"has_rated_selected": False},
                status=status.HTTP_200_OK
            )

        user = request.user

        # check if user rated at least ONE of selected movies
        rated_count = UserMovieRating.objects.filter(
            user=user,
            movie_id__in=selected_ids
        ).count()

        return Response(
            {"has_rated_selected": rated_count > 0},
            status=status.HTTP_200_OK
        )
