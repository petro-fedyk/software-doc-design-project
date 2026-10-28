import logging
from django.db import IntegrityError, OperationalError
from rest_framework.response import Response
from rest_framework.views import exception_handler
from pharmacy.domain.core import DomainError


def handle_exception(exc, context):
    if isinstance(exc, DomainError):
        return Response({"code": exc.code, "detail": str(exc)}, status=exc.status)
    if isinstance(exc, IntegrityError):
        return Response(
            {
                "code": "DATA_CONFLICT",
                "detail": "Constraint violation or duplicate value.",
            },
            status=409,
        )
    if isinstance(exc, OperationalError):
        logging.getLogger(__name__).warning(
            "Database operation failed (%s)", type(exc).__name__
        )
        return Response(
            {"code": "DATABASE_UNAVAILABLE", "detail": "Retry the request."}, status=503
        )
    return exception_handler(exc, context)
