from rest_framework import serializers

class ContentBasedRecommendationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    genres = serializers.CharField(allow_blank=True)
    year = serializers.IntegerField(allow_null=True)
    score = serializers.FloatField()
