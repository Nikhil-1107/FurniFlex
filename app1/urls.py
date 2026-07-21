from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('products/', views.product_list, name='product_list'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('rent/<int:pk>/', views.rent_product, name='rent_product'),
    path('checkout/<int:order_id>/', views.checkout, name='checkout'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('my-rentals/', views.my_rentals, name='my_rentals'),
    path('my-rentals/renew/<int:rental_id>/', views.renew_rental, name='renew_rental'),
    path('my-rentals/renewal-payment-success/', views.renewal_payment_success, name='renewal_payment_success'),
    path('profile/', views.profile, name='profile'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('support/', views.support_tickets, name='support_tickets'),
    path('repair-ticket/<int:rental_id>/', views.create_repair_ticket, name='create_repair_ticket'),
    path('clear-notifications/', views.clear_notifications, name='clear_notifications'),
    path('clear-all-notifications/', views.clear_all_notifications, name='clear_all_notifications'),
    
    # Auth URLs
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='registration/change_password.html',
        success_url='/profile/'
    ), name='change_password'),
]
