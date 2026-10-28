from django.urls import include, path
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from pharmacy.api import views as v

router = DefaultRouter()
for prefix, view in [
    ("products", v.ProductViewSet),
    ("pharmacies", v.PharmacyViewSet),
    ("categories", v.CategoryViewSet),
    ("manufacturers", v.ManufacturerViewSet),
    ("orders", v.OrderViewSet),
    ("admin/assignments", v.AssignmentViewSet),
    ("admin/promotions", v.PromotionViewSet),
    ("admin/loyalty-tiers", v.TierViewSet),
    ("admin/promotion-products", v.PromotionProductViewSet),
    ("admin/users", v.UserAdminViewSet),
    ("admin/delivery-rules", v.DeliveryRuleViewSet),
]:
    router.register(prefix, view, basename=prefix.replace("/", "-"))
urlpatterns = [
    path("api/", include(router.urls)),
    path("api/health/", v.HealthView.as_view()),
    path("api/auth/register/", v.RegisterView.as_view()),
    path("api/auth/token/", v.LoginView.as_view()),
    path("api/me/", v.MeView.as_view()),
    path("api/checkout/quote/", v.QuoteView.as_view()),
    path("api/cart/", v.CartView.as_view()),
    path("api/pharmacies/<int:pharmacy_id>/inventory/", v.InventoryView.as_view()),
    path(
        "api/pharmacies/<int:pharmacy_id>/inventory/<int:product_id>/",
        v.InventoryChangeView.as_view(),
    ),
    path("api/preferences/", v.PreferencesView.as_view()),
    path("api/availability-watches/", v.WatchView.as_view()),
    path("api/reminders/", v.ReminderView.as_view()),
    path("api/notifications/", v.NotificationsView.as_view()),
    path(
        "api/notifications/<int:notification_id>/read/",
        v.NotificationReadView.as_view(),
    ),
    path("api/loyalty/", v.LoyaltyView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view()),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
urlpatterns[-2].name = "schema"

urlpatterns += [
    path("api/profile/", v.ProfileView.as_view()),
    path("api/guest-cart/", v.GuestCartView.as_view()),
    path("api/prescriptions/", v.SavedPrescriptionView.as_view()),
    path(
        "api/prescriptions/<int:prescription_id>/",
        v.SavedPrescriptionDeleteView.as_view(),
    ),
    path("api/orders/<int:order_id>/reorder/", v.ReorderView.as_view()),
    path("api/payment-methods/", v.PaymentMethodsView.as_view()),
    path("api/pharmacies/<int:pharmacy_id>/statistics/", v.StatisticsView.as_view()),
    path("api/admin/statistics/", v.StatisticsView.as_view()),
    path("api/pharmacies/<int:pharmacy_id>/audit/", v.AuditView.as_view()),
    path("api/admin/audit/", v.AuditView.as_view()),
]
