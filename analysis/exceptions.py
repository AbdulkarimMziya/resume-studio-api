from rest_framework.exceptions import APIException

class AIBadOutput(APIException):
    status_code = 502
    default_detail = "The AI service returned an invalid response. Please try again."
    default_code = "invalid_ai_response"

class AIUnavailable(APIException):
    status_code = 503
    default_detail = "The AI service is unavailable right now. Please try again shortly."
    default_code = "ai_unavailable"


