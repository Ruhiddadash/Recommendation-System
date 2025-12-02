from rest_framework import serializers

class RecommendationRequestSerializer(serializers.Serializer):
    selected_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True, allow_empty=False
    )
    top_k = serializers.IntegerField(required=False, default=16)

class MovieRecommendationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    genres = serializers.CharField(allow_null=True, required=False)
    score = serializers.FloatField(required=False)  # optional relevance score
