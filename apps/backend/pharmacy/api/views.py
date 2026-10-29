from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction, connection
from django.db.models import Q, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiParameter
from pharmacy import models as m
from pharmacy.api import serializers as s
from pharmacy.api.auth import actor, issue_token
from pharmacy.composition import Services
from pharmacy.domain.core import DomainError

ERROR_RESPONSES = {
    400: OpenApiTypes.OBJECT,
    401: s.ErrorSerializer,
    403: s.ErrorSerializer,
    404: s.ErrorSerializer,
    409: s.ErrorSerializer,
    503: s.ErrorSerializer,
}


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role == "ADMIN")


def validated(serializer, request):
    obj = serializer(data=request.data)
    obj.is_valid(raise_exception=True)
    return obj.validated_data


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(responses=OpenApiTypes.OBJECT, auth=[])
    def get(self, request):
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return Response({"status": "ok", "database": "mysql"})


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    @extend_schema(
        request=s.RegisterSerializer, responses={201: s.TokenSerializer}, auth=[]
    )
    def post(self, request):
        data = validated(s.RegisterSerializer, request)
        with transaction.atomic():
            user = m.Users.objects.create(
                username=data["username"],
                email=data["email"],
                password=make_password(data["password"]),
                role="CUSTOMER",
                is_staff=False,
                is_active=True,
                created_at=timezone.now(),
            )
            m.CustomerProfiles.objects.create(user=user, full_name=data["full_name"])
            m.NotificationPreferences.objects.create(
                user=user, promotions_enabled=False, reminders_enabled=False
            )
            tier = m.LoyaltyTiers.objects.filter(code="STANDARD").first()
            if tier:
                m.LoyaltyAccounts.objects.create(customer=user, tier=tier, balance=0)
        return Response(
            {"access": issue_token(user), "expires_in": settings.JWT_TTL_SECONDS},
            status=201,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [LoginThrottle]

    @extend_schema(request=s.LoginSerializer, responses=s.TokenSerializer, auth=[])
    def post(self, request):
        data = validated(s.LoginSerializer, request)
        user = m.Users.objects.filter(username=data["username"], is_active=True).first()
        valid = (
            check_password(data["password"], user.password)
            if user
            else check_password(
                data["password"], make_password("unusable-timing-placeholder")
            )
        )
        if not user or not valid:
            return Response({"code": "INVALID_CREDENTIALS"}, status=401)
        return Response(
            {"access": issue_token(user), "expires_in": settings.JWT_TTL_SECONDS}
        )


class MeView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        current = actor(request.user)
        return Response(
            {
                "id": current.id,
                "username": request.user.username,
                "email": request.user.email,
                "role": current.role,
                "pharmacy_ids": sorted(current.pharmacies),
                "pharmacist": current.pharmacist,
            }
        )


class PublicReadAdminWrite(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        return (
            [permissions.AllowAny()]
            if self.action in ("list", "retrieve", "availability")
            else [AdminPermission()]
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            serializer.save()

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()


class ProductViewSet(PublicReadAdminWrite):
    serializer_class = s.ProductSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("category", int, description="Filter by category ID."),
            OpenApiParameter("manufacturer", int, description="Filter by manufacturer ID."),
            OpenApiParameter("prescription_required", bool, description="Filter by prescription requirement."),
            OpenApiParameter("search", str, description="Case-insensitive product name or SKU search."),
        ],
        responses={
            200: s.ProductPageSerializer,
            400: OpenApiTypes.OBJECT,
            401: s.ErrorSerializer,
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def perform_update(self, serializer):
        with transaction.atomic():
            product = m.Products.objects.select_for_update().get(
                id=serializer.instance.id
            )
            restricted = {"prescription_required", "storage_min_c", "storage_max_c"}
            changed = any(
                k in serializer.validated_data
                and serializer.validated_data[k] != getattr(product, k)
                for k in restricted
            )
            if (
                changed
                and m.OrderItems.objects.filter(product=product)
                .exclude(order__status__in=["COMPLETED", "CANCELLED"])
                .exists()
            ):
                raise DomainError("ACTIVE_ORDER_PRODUCT_RESTRICTIONS_LOCKED")
            serializer.save()

    def get_queryset(self):
        qs = m.Products.objects.all().order_by("id")
        if not self.request.user or self.request.user.role != "ADMIN":
            qs = qs.filter(is_active=True)
        for key in ("category", "manufacturer"):
            value = self.request.query_params.get(key)
            if value:
                try:
                    identifier = int(value)
                except ValueError:
                    raise serializers.ValidationError(
                        {key: "Use a numeric identifier."}
                    )
                qs = qs.filter(**{key + "_id": identifier})
        prescription = self.request.query_params.get("prescription_required")
        if prescription is not None:
            if prescription not in ("true", "false"):
                raise serializers.ValidationError(
                    {"prescription_required": "Use true or false."}
                )
            qs = qs.filter(prescription_required=prescription == "true")
        if self.request.query_params.get("search"):
            qs = qs.filter(
                Q(name__icontains=self.request.query_params["search"])
                | Q(sku__icontains=self.request.query_params["search"])
            )
        return qs

    @extend_schema(
        responses={200: s.ProductAvailabilitySerializer(many=True), **ERROR_RESPONSES},
        filters=False,
    )
    @action(detail=True, methods=["get"], pagination_class=None)
    def availability(self, request, pk=None):
        product = self.get_object()
        rows = m.PharmacyInventory.objects.filter(
            product=product, is_listed=True, pharmacy__is_active=True
        ).annotate(available=F("on_hand") - F("reserved"))
        return Response(
            list(
                rows.values("pharmacy_id", "pharmacy__name", "unit_price", "available")[
                    :500
                ]
            )
        )


class PharmacyViewSet(PublicReadAdminWrite):
    serializer_class = s.PharmacySerializer

    def get_queryset(self):
        qs = m.Pharmacies.objects.all().order_by("id")
        return (
            qs
            if self.request.user and self.request.user.role == "ADMIN"
            else qs.filter(is_active=True)
        )


class CategoryViewSet(PublicReadAdminWrite):
    serializer_class = s.CategorySerializer
    queryset = m.Categories.objects.order_by("id")


class ManufacturerViewSet(PublicReadAdminWrite):
    serializer_class = s.ManufacturerSerializer
    queryset = m.Manufacturers.objects.order_by("id")


class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = [AdminPermission]
    http_method_names = ["get", "post", "patch", "head", "options"]


class AssignmentViewSet(AdminViewSet):
    serializer_class = s.AssignmentSerializer
    queryset = m.EmployeeAssignments.objects.order_by("id")

    def perform_create(self, serializer):
        serializer.save(created_at=timezone.now())


class PromotionViewSet(AdminViewSet):
    serializer_class = s.PromotionSerializer
    queryset = m.Promotions.objects.order_by("id")

    def perform_create(self, serializer):
        from pharmacy.infrastructure.repositories import DjangoUnitOfWork

        with DjangoUnitOfWork() as uow:
            promotion = serializer.save()
            uow.outbox.add("promotion.published", {"promotion_id": promotion.id})
            uow.commit()


class TierViewSet(AdminViewSet):
    serializer_class = s.TierSerializer
    queryset = m.LoyaltyTiers.objects.order_by("id")


class PromotionProductViewSet(AdminViewSet):
    serializer_class = s.PromotionProductSerializer
    queryset = m.PromotionProducts.objects.order_by("id")


class QuoteView(APIView):
    @extend_schema(request=s.QuoteSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        return Response(
            Services().orders.quote(
                actor(request.user), validated(s.QuoteSerializer, request)
            )
        )


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = s.OrderSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return m.Orders.objects.none()
        user = actor(self.request.user)
        qs = m.Orders.objects.order_by("-id")
        if user.role == "CUSTOMER":
            return qs.filter(customer_id=user.id)
        if user.role == "STAFF":
            return qs.filter(pharmacy_id__in=user.pharmacies)
        return qs

    @extend_schema(request=s.PlaceSerializer, responses={201: OpenApiTypes.OBJECT})
    def create(self, request):
        return Response(
            Services().orders.place(
                actor(request.user), validated(s.PlaceSerializer, request)
            ),
            status=201,
        )

    @extend_schema(request=s.TransitionSerializer, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        self.get_object()
        return Response(
            Services().orders.transition(
                actor(request.user),
                int(pk),
                validated(s.TransitionSerializer, request)["status"],
            )
        )

    @extend_schema(request=s.PaymentSerializer, responses={202: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        self.get_object()
        return Response(
            Services().payments.request(
                actor(request.user),
                int(pk),
                validated(s.PaymentSerializer, request)["idempotency_key"],
            ),
            status=202,
        )

    @extend_schema(request=s.RefundSerializer, responses={202: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        self.get_object()
        data = validated(s.RefundSerializer, request)
        return Response(
            Services().payments.refund(
                actor(request.user),
                int(pk),
                data["amount"],
                data["reason"],
                data["idempotency_key"],
            ),
            status=202,
        )

    @extend_schema(request=s.VerificationSerializer, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["post"], url_path="verify-prescription")
    def verify_prescription(self, request, pk=None):
        self.get_object()
        return Response(
            Services().orders.verify(
                actor(request.user),
                int(pk),
                validated(s.VerificationSerializer, request)["approved"],
            )
        )

    @extend_schema(request=None, responses={202: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        self.get_object()
        if request.data:
            raise serializers.ValidationError("This action takes no input.")
        return Response(
            Services().orders.ship(actor(request.user), int(pk)), status=202
        )

    @extend_schema(responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=["get"])
    def fulfillment(self, request, pk=None):
        order = self.get_object()
        return Response(
            {
                "payments": list(
                    m.Payments.objects.filter(order=order).values(
                        "id", "status", "provider", "amount"
                    )
                ),
                "delivery": m.Deliveries.objects.filter(order=order)
                .values("method", "status", "tracking_reference")
                .first(),
                "refunds": list(
                    m.Refunds.objects.filter(payment__order=order).values(
                        "id", "amount", "status"
                    )
                ),
            }
        )


class InventoryView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: s.ObjectSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request, pharmacy_id):
        if request.user and request.user.role in {"STAFF", "ADMIN"}:
            actor(request.user).branch(pharmacy_id)
            rows = m.PharmacyInventory.objects.filter(pharmacy_id=pharmacy_id).annotate(
                available=F("on_hand") - F("reserved")
            )
            return Response(
                list(
                    rows.values(
                        "id",
                        "product_id",
                        "product__name",
                        "unit_price",
                        "on_hand",
                        "reserved",
                        "is_listed",
                        "available",
                    )[:500]
                )
            )
        rows = m.PharmacyInventory.objects.filter(
            pharmacy_id=pharmacy_id,
            is_listed=True,
            pharmacy__is_active=True,
            product__is_active=True,
        ).annotate(available=F("on_hand") - F("reserved"))
        return Response(
            list(
                rows.values("product_id", "product__name", "unit_price", "available")[
                    :500
                ]
            )
        )


class InventoryChangeView(APIView):
    @extend_schema(request=s.InventoryChangeSerializer, responses=OpenApiTypes.OBJECT)
    def patch(self, request, pharmacy_id, product_id):
        return Response(
            Services().inventory.change(
                actor(request.user),
                pharmacy_id,
                product_id,
                validated(s.InventoryChangeSerializer, request),
            )
        )


class CartView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        actor(request.user).customer()
        return Response(
            {
                "items": list(
                    m.CartItems.objects.filter(cart__customer=request.user).values(
                        "product_id", "quantity"
                    )
                )
            }
        )

    @extend_schema(request=s.CartChangeSerializer, responses=OpenApiTypes.OBJECT)
    def put(self, request):
        data = validated(s.CartChangeSerializer, request)
        return Response(
            Services().customers.cart(
                actor(request.user),
                data["product_id"],
                data["quantity"],
                allow_unavailable=data.get("allow_unavailable", False),
            )
        )


class PersonalView(APIView):
    serializer_class = s.ObjectSerializer
    kind = None

    def get(self, request):
        actor(request.user).customer()
        if self.kind == "preferences":
            rows = m.NotificationPreferences.objects.filter(user=request.user)
        elif self.kind == "watch":
            rows = m.AvailabilitySubscriptions.objects.filter(customer=request.user)
        else:
            rows = m.Reminders.objects.filter(customer=request.user)
        return Response(list(rows.values()[:100]))

    def post(self, request):
        return Response(
            Services().customers.personal(
                actor(request.user),
                self.kind,
                validated(self.serializer_class, request),
            )
        )


class PreferencesView(PersonalView):
    kind = "preferences"
    serializer_class = s.PreferencesSerializer

    @extend_schema(responses={200: s.PreferenceRowSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request):
        return super().get(request)


class WatchView(PersonalView):
    kind = "watch"
    serializer_class = s.WatchSerializer

    @extend_schema(responses={200: s.WatchRowSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request):
        return super().get(request)


class ReminderView(PersonalView):
    kind = "reminder"
    serializer_class = s.ReminderSerializer

    @extend_schema(responses={200: s.ReminderRowSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request):
        return super().get(request)


class NotificationsView(APIView):
    @extend_schema(responses={200: s.NotificationRowSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request):
        return Response(
            list(
                m.Notifications.objects.filter(user=request.user)
                .order_by("-id")
                .values("id", "user_id", "type", "title", "body", "read_at", "created_at")[:100]
            )
        )


class NotificationReadView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, notification_id):
        row = get_object_or_404(m.Notifications, id=notification_id, user=request.user)
        row.read_at = timezone.now()
        row.save(update_fields=["read_at"])
        return Response({"read": True})


class LoyaltyView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        actor(request.user).customer()
        return Response(
            {
                "account": m.LoyaltyAccounts.objects.filter(customer=request.user)
                .values("balance", "tier__code")
                .first(),
                "transactions": list(
                    m.LoyaltyTransactions.objects.filter(account__customer=request.user)
                    .order_by("-id")
                    .values()[:100]
                ),
            }
        )


class UserAdminViewSet(AdminViewSet):
    serializer_class = s.UserAdminSerializer
    queryset = m.Users.objects.order_by("id")


class DeliveryRuleViewSet(AdminViewSet):
    serializer_class = s.DeliveryRuleSerializer
    queryset = m.DeliveryRules.objects.order_by("id")


class ProfileView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        actor(request.user).customer()
        return Response(
            m.CustomerProfiles.objects.filter(user=request.user)
            .values("full_name", "phone", "preferred_pharmacy_id")
            .first()
            or {}
        )

    @extend_schema(request=s.ProfileSerializer, responses=OpenApiTypes.OBJECT)
    def patch(self, request):
        actor(request.user).customer()
        data = validated(s.ProfileSerializer, request)
        if data.get("preferred_pharmacy_id"):
            get_object_or_404(
                m.Pharmacies, id=data["preferred_pharmacy_id"], is_active=True
            )
        with transaction.atomic():
            m.Users.objects.select_for_update().get(id=request.user.id)
            row, created = m.CustomerProfiles.objects.get_or_create(
                user=request.user, defaults={"full_name": request.user.username}
            )
            for key, value in data.items():
                setattr(row, key, value)
            row.save()
        return Response(
            {
                "full_name": row.full_name,
                "phone": row.phone,
                "preferred_pharmacy_id": row.preferred_pharmacy_id,
            }
        )


class SavedPrescriptionView(APIView):
    @extend_schema(responses={200: s.SavedPrescriptionRowSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request):
        actor(request.user).customer()
        return Response(
            list(
                m.PrescriptionRecords.objects.filter(customer=request.user).values()[
                    :100
                ]
            )
        )

    @extend_schema(
        request=s.SavedPrescriptionSerializer, responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        from uuid import uuid4

        actor(request.user).customer()
        data = validated(s.SavedPrescriptionSerializer, request)
        row = m.PrescriptionRecords.objects.create(
            customer=request.user,
            display_label=data["display_label"],
            masked_reference="SIM-" + uuid4().hex[:12],
            is_demo=True,
            created_at=timezone.now(),
        )
        return Response(
            {
                "id": row.id,
                "display_label": row.display_label,
                "masked_reference": row.masked_reference,
                "is_demo": True,
            },
            status=201,
        )


class SavedPrescriptionDeleteView(APIView):
    @extend_schema(responses={204: None})
    def delete(self, request, prescription_id):
        actor(request.user).customer()
        get_object_or_404(
            m.PrescriptionRecords, id=prescription_id, customer=request.user
        ).delete()
        return Response(status=204)


class ReorderView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, order_id):
        current = actor(request.user)
        current.customer()
        order = get_object_or_404(m.Orders, id=order_id, customer=request.user)
        with transaction.atomic():
            for item in m.OrderItems.objects.filter(order=order):
                Services().customers.cart(current, item.product_id, item.quantity)
        return Response(
            {
                "status": "CART_UPDATED",
                "detail": "Quote current prices before placing the new order.",
            }
        )


class GuestCartView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def read(self, request):
        from django.core import signing

        try:
            return signing.loads(
                request.COOKIES.get("guest_cart", ""), salt="guest-cart", max_age=86400
            )
        except signing.BadSignature:
            return {}

    @extend_schema(responses=OpenApiTypes.OBJECT, auth=[])
    def get(self, request):
        return Response({"items": self.read(request)})

    @extend_schema(
        request=s.CartChangeSerializer, responses=OpenApiTypes.OBJECT, auth=[]
    )
    def put(self, request):
        from django.core import signing

        data = validated(s.CartChangeSerializer, request)
        get_object_or_404(m.Products, id=data["product_id"], is_active=True)
        items = self.read(request)
        if data["quantity"]:
            items[str(data["product_id"])] = data["quantity"]
        else:
            items.pop(str(data["product_id"]), None)
        if len(items) > 50:
            raise DomainError("CART_LIMIT", status=400)
        response = Response({"items": items})
        response.set_cookie(
            "guest_cart",
            signing.dumps(items, salt="guest-cart"),
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure(),
        )
        return response

    @extend_schema(request=None, responses={204: None}, auth=[])
    def delete(self, request):
        response = Response(status=204)
        response.delete_cookie("guest_cart", samesite="Lax")
        return response


class StatisticsView(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pharmacy_id=None):
        from django.db.models import Sum, Count

        current = actor(request.user)
        if pharmacy_id:
            current.branch(pharmacy_id)
        else:
            current.admin()
        orders = m.Orders.objects.all()
        if pharmacy_id:
            orders = orders.filter(pharmacy_id=pharmacy_id)
        return Response(
            {
                "by_status": list(orders.values("status").annotate(count=Count("id"))),
                "completed_order_total": orders.filter(status="COMPLETED").aggregate(
                    total=Sum("grand_total")
                )["total"]
                or 0,
            }
        )


class AuditView(APIView):
    @extend_schema(responses={200: s.AuditRowSerializer(many=True), **ERROR_RESPONSES})
    def get(self, request, pharmacy_id=None):
        current = actor(request.user)
        rows = m.AuditEntries.objects.order_by("-id")
        if pharmacy_id:
            current.branch(pharmacy_id)
            rows = rows.filter(
                Q(
                    target_type="order",
                    target_id__in=m.Orders.objects.filter(
                        pharmacy_id=pharmacy_id
                    ).values("id"),
                )
                | Q(
                    target_type="inventory",
                    target_id__in=m.PharmacyInventory.objects.filter(
                        pharmacy_id=pharmacy_id
                    ).values("id"),
                )
            )
        else:
            current.admin()
        return Response(list(rows.values()[:100]))


class PaymentMethodsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(
            {"methods": sorted(settings.ENABLED_PAYMENT_METHODS), "simulated": True}
        )
