"""
Basic HTTP Authentication Middleware for Production
"""
import base64
from django.http import HttpResponse
from django.conf import settings


class BasicAuthMiddleware:
    """
    Simple HTTP Basic Authentication middleware for production.
    Prompts for username/password before allowing access.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only enable if BASIC_AUTH_ENABLED is True
        if not getattr(settings, 'BASIC_AUTH_ENABLED', False):
            return self.get_response(request)

        # Check if Authorization header exists
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2 and auth[0].lower() == 'basic':
                # Decode credentials
                try:
                    username, password = base64.b64decode(auth[1]).decode('utf-8').split(':', 1)

                    # Check against configured credentials
                    expected_username = getattr(settings, 'BASIC_AUTH_USERNAME', 'admin')
                    expected_password = getattr(settings, 'BASIC_AUTH_PASSWORD', 'changeme')

                    if username == expected_username and password == expected_password:
                        # Authentication successful
                        return self.get_response(request)
                except (ValueError, UnicodeDecodeError):
                    pass

        # Authentication required
        response = HttpResponse('Unauthorized', status=401)
        response['WWW-Authenticate'] = 'Basic realm="Care Plan Generator - Lamar Health"'
        return response
