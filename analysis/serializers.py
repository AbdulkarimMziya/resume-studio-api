import os

from rest_framework import serializers

RESUME_MAX_CHARS = 30_000


class AnalyzeRequestSerializer(serializers.Serializer):
    resume_text = serializers.CharField(max_length=RESUME_MAX_CHARS)
    job_description = serializers.CharField(max_length=20_000)


class SuggestionSerializer(serializers.Serializer):
    original = serializers.CharField()
    replacement = serializers.CharField()
    reason = serializers.CharField()


class AnalyzeResponseSerializer(serializers.Serializer):
    suggestions = SuggestionSerializer(many=True)


ALLOWED_UPLOAD_EXTENSIONS = {".txt", ".docx", ".pdf"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024    # 2 MB


class ExtractTextRequestSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):
        ext = os.path.splitext(file.name)[1].lower()        # "CV.PDF" -> ".pdf"
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise serializers.ValidationError("Only .txt, .docx and .pdf files are supported.")
        if file.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("That file is too large (max 2 MB).")
        return file


class ExtractTextResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
