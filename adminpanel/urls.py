from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="admin_dashboard"),
    path("login/", views.admin_login, name="admin_login"),
    path("products/", views.products, name="admin_products"),
    path("products/add/", views.product_add, name="admin_product_add"),
    path("products/edit/<int:pk>/", views.product_edit, name="admin_product_edit"),
    path("products/delete/<int:pk>/", views.product_delete, name="admin_product_delete"),
    path("rentals/", views.rentals, name="admin_rentals"),
    path("rentals/update-status/<int:pk>/", views.update_rental_status, name="admin_update_rental_status"),
    path("rentals/mark-paid/<int:pk>/", views.mark_rental_paid, name="admin_mark_rental_paid"),
    path("tickets/", views.tickets, name="admin_tickets"),
    path("tickets/resolve/<int:pk>/", views.resolve_ticket, name="admin_resolve_ticket"),
    path("users/", views.users, name="admin_users"),
    path("users/add/", views.user_add, name="admin_user_add"),
    path("users/edit/<int:pk>/", views.user_edit, name="admin_user_edit"),
    path("users/delete/<int:pk>/", views.user_delete, name="admin_user_delete"),
    path("queries/", views.contact_queries, name="admin_queries"),
    path("queries/reply/<int:pk>/", views.send_query_reply, name="admin_send_query_reply"),
]
