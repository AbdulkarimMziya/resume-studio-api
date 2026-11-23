from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    RESUME_MAX_CHARS,
    AnalyzeRequestSerializer,
    AnalyzeResponseSerializer,
    ExtractTextRequestSerializer,
    ExtractTextResponseSerializer,
)
from .services import analyze_resume
from .documents import extract_text
from .exceptions import UnreadableFile

from drf_spectacular.utils import extend_schema, OpenApiResponse

class AnalyzeView(APIView):
    @extend_schema(
        request=AnalyzeRequestSerializer,
        responses={
            200: AnalyzeResponseSerializer,
            400: OpenApiResponse(description="Missing, blank or too long resume_text or job_description"),
            502: OpenApiResponse(
                description="The AI returned an unusable response (invalid shape, or a suggestion "
                "that doesn't match the resume). Nothing was wrong with the request; it can be retried."
            ),
            503: OpenApiResponse(
                description="The AI service couldn't be reached (timeout, outage or quota). "
                "Try again shortly."
            ),
        },
    )
    def post(self, request: Request):
        application_data = request.data

        serializer = AnalyzeRequestSerializer(data=application_data)
        serializer.is_valid(raise_exception=True)
        result = analyze_resume(
                serializer.validated_data['resume_text'], 
                serializer.validated_data['job_description']
            )
        return Response(
            result,
            status=status.HTTP_200_OK,
        )


class ExtractTextView(APIView):
    # Files can't travel in JSON, so this endpoint only accepts multipart form data.
    # Anything else (e.g. a JSON body) gets a 415 Unsupported Media Type from DRF.
    parser_classes = [MultiPartParser]

    @extend_schema(
        request={"multipart/form-data": ExtractTextRequestSerializer},
        responses={
            200: ExtractTextResponseSerializer,
            400: OpenApiResponse(
                description="No file, wrong type (only .txt, .docx, .pdf), over 2 MB, damaged or "
                "image-only file, or more text than the 30,000-character resume limit"
            ),
            415: OpenApiResponse(description="The body wasn't multipart/form-data"),
        },
    )
    def post(self, request: Request):
        serializer = ExtractTextRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)              # type and size -> 400 {"file": [...]}

        text = extract_text(serializer.validated_data["file"])  # unreadable -> 400 {"detail": ...}
        if len(text) > RESUME_MAX_CHARS:
            raise UnreadableFile(
                f"That file has {len(text):,} characters of text, more than the "
                f"{RESUME_MAX_CHARS:,}-character limit. Upload just your resume, or paste a shorter version."
            )
        return Response({"text": text}, status=status.HTTP_200_OK)
