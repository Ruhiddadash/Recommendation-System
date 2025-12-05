from rest_framework import serializers

class RecommendationRequestSerializer(serializers.Serializer):
    selected_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True, allow_empty=False
    )
    top_k = serializers.IntegerField(required=False, default=16)


class MovieRecommendationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    year = serializers.IntegerField(allow_null=True)
    genres = serializers.CharField(allow_blank=True)

    predicted_rating = serializers.FloatField()
    badge = serializers.CharField()
    reason = serializers.CharField()
    score = serializers.FloatField()

