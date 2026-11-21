from rest_framework import serializers


class AnalyzeRequestSerializer(serializers.Serializer):
    resume_text = serializers.CharField(max_length=30_000)
    job_description = serializers.CharField(max_length=20_000)


class SuggestionSerializer(serializers.Serializer):
    original = serializers.CharField()
    replacement = serializers.CharField()
    reason = serializers.CharField()


class AnalyzeResponseSerializer(serializers.Serializer):
    suggestions = SuggestionSerializer(many=True)
