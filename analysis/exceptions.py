from rest_framework.exceptions import APIException

class AIBadOutput(APIException):
    status_code = 502
    default_detail = "The AI service returned an invalid response. Please try again."
    default_code = "invalid_ai_response"

class AIUnavailable(APIException):
    status_code = 503
    default_detail = "The AI service is unavailable right now. Please try again shortly."
    default_code = "ai_unavailable"



class UnreadableFile(APIException):
    # The upload passed the type/size checks but its text couldn't be read: the user can fix this
    status_code = 400
    default_detail = "Couldn't read that file."
    default_code = "unreadable_file"
