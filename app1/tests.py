from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from app1.models import Product, RentalOrder, RepairTicket, UserProfile
from furniflex.context_processors import user_notifications

class NotificationTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username="test_user", password="test_password")
        self.client = Client()
        
        # Create product
        self.product = Product.objects.create(
            name="Luxurious Sofa",
            category="Sofa",
            price_per_month=1500.00,
            stock=5,
            available_durations="3,6,12",
            description="Premium fabric sofa."
        )

    def test_clear_all_notifications(self):
        # Log in
        self.client.login(username="test_user", password="test_password")
        
        # Create active rental order to trigger a notification
        rental = RentalOrder.objects.create(
            user=self.user,
            product=self.product,
            rental_duration_months=6,
            status="Active"
        )
        
        # Mock request object
        class MockRequest:
            def __init__(self, user):
                self.user = user
        
        request = MockRequest(self.user)
        
        # Get notifications via context processor (expecting points_earned and loyalty_alert)
        context = user_notifications(request)
        self.assertEqual(len(context['user_notifications']), 2)
        
        keys = [notif['key'] for notif in context['user_notifications']]
        self.assertIn(f"points_earned_{rental.id}", keys)
        self.assertIn("loyalty_alert_600", keys)
        
        # Post to clear-all-notifications endpoint
        response = self.client.post(reverse('clear_all_notifications'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Get notifications again and verify they are cleared
        context_after = user_notifications(request)
        self.assertEqual(len(context_after['user_notifications']), 0)
        
        # Verify that UserProfile now has the notifications in dismissed_notifications
        profile = UserProfile.objects.get(user=self.user)
        self.assertIn(f"points_earned_{rental.id}", profile.dismissed_notifications)
        self.assertIn("loyalty_alert_600", profile.dismissed_notifications)

    def test_new_user_discount(self):
        # Log in
        self.client.login(username="test_user", password="test_password")
        
        # 1. First order: should get 20% discount on the first month
        response = self.client.post(reverse('rent_product', args=[self.product.id]), {'duration': 3})
        # Check that we redirect to checkout
        self.assertEqual(response.status_code, 302)
        
        # Get the created order (should be status Pending)
        order = RentalOrder.objects.filter(user=self.user, status='Pending').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.rental_duration_months, 3)
        
        # Price: 1500 per month.
        # First month: 20% discount = 1500 * 0.20 = 300 discount.
        # Total: (1500 * 3) - 300 = 4200.
        from decimal import Decimal
        self.assertEqual(order.discount_amount, Decimal('300.00'))
        self.assertEqual(order.total_amount, Decimal('4200.00'))
        
        # Verify the checkout page shows the correct amounts
        checkout_response = self.client.get(reverse('checkout', args=[order.id]))
        self.assertEqual(checkout_response.status_code, 200)
        self.assertEqual(checkout_response.context['discount_amount'], Decimal('300.00'))
        self.assertEqual(checkout_response.context['total_amount'], Decimal('4200.00'))
        
        # Confirm order (e.g. via COD payment confirmation)
        confirm_response = self.client.post(reverse('checkout', args=[order.id]), {
            'address_id': 'new',
            'new_address': '123 Test St',
            'city': 'Testville',
            'state': 'TestState',
            'pincode': '123456',
            'payment_method': 'COD'
        })
        self.assertEqual(confirm_response.status_code, 302)
        
        # The order should now be active
        order.refresh_from_db()
        self.assertEqual(order.status, 'Active')
        
        # 2. Second order: should NOT get any new user discount since there is an active order
        response2 = self.client.post(reverse('rent_product', args=[self.product.id]), {'duration': 3})
        self.assertEqual(response2.status_code, 302)
        
        order2 = RentalOrder.objects.filter(user=self.user, status='Pending').first()
        self.assertIsNotNone(order2)
        self.assertEqual(order2.discount_amount, Decimal('0.00'))
        self.assertEqual(order2.total_amount, Decimal('4500.00'))
