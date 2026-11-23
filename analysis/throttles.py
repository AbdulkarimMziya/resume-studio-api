"""Rate limits. Each analysis costs a Gemini call on our key, so visitors get a fair share.

Users are anonymous, so limits are per IP address (see NUM_PROXIES in settings for how the
IP is found behind Render's proxy). The rates live in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
"""
from rest_framework.throttling import AnonRateThrottle


class AnalyzeBurstThrottle(AnonRateThrottle):
    scope = "analyze_burst"         # e.g. 5/min per IP: stops rapid clicks and scripts


class AnalyzeDailyThrottle(AnonRateThrottle):
    scope = "analyze_daily"         # e.g. 50/day per IP: one person can't use the whole budget


class AnalyzeGlobalThrottle(AnonRateThrottle):
    scope = "analyze_global"        # e.g. 500/day for EVERYONE together: a hard cap on Gemini calls

    def get_cache_key(self, request, view):
        # One shared counter instead of one per IP, so rotating IPs can't get around it
        return self.cache_format % {"scope": self.scope, "ident": "all"}


class ExtractTextThrottle(AnonRateThrottle):
    scope = "extract"               # e.g. 20/min per IP: no Gemini cost, but PDF parsing uses CPU
