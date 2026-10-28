from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4
import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from pharmacy import models as m
from pharmacy.domain.core import Actor


def fingerprint(user):
    return sha256(user.password.encode()).hexdigest()


def issue_token(user):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(seconds=settings.JWT_TTL_SECONDS),
            "jti": str(uuid4()),
            "iss": "internet-pharmacy",
            "aud": "pharmacy-api",
            "type": "access",
            "pwd": fingerprint(user),
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def actor(user):
    return Actor(
        user.id,
        user.role,
        frozenset(
            m.EmployeeAssignments.objects.filter(
                user=user, is_active=True, pharmacy__is_active=True
            ).values_list("pharmacy_id", flat=True)
        ),
        user.id in settings.PHARMACIST_IDS,
    )


class JWTAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return "Bearer"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts:
            return None
        if len(parts) != 2 or parts[0].lower() != b"bearer":
            raise AuthenticationFailed("Invalid authorization header")
        try:
            data = jwt.decode(
                parts[1],
                settings.SECRET_KEY,
                algorithms=["HS256"],
                audience="pharmacy-api",
                issuer="internet-pharmacy",
                options={"require": ["sub", "iat", "exp", "type", "pwd"]},
            )
            if data["type"] != "access":
                raise ValueError()
            user = m.Users.objects.filter(id=int(data["sub"]), is_active=True).first()
            if user is None or data["pwd"] != fingerprint(user):
                raise ValueError()
        except (jwt.PyJWTError, ValueError, TypeError, OverflowError):
            raise AuthenticationFailed("Invalid or expired access token")
        return user, data


class JWTAuthenticationSchema(OpenApiAuthenticationExtension):
    target_class = "pharmacy.api.auth.JWTAuthentication"
    name = "bearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
