from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from .serializers import AnalyzeRequestSerializer, AnalyzeResponseSerializer
from .services import analyze_resume

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
