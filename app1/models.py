from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    street_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.street_address}, {self.city}"

# Create your models here.

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Sofa', 'Sofa'),
        ('Bed', 'Bed'),
        ('Dining', 'Dining Table'),
        ('Table', 'Tables & Desks'),
        ('Living', 'Living Room'),
        ('Office', 'Office & Study'),
        ('Appliances', 'Appliances'),
        ('Others', 'Others'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Rent (₹/month)")
    material = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    stock = models.PositiveIntegerField(default=10)
    available_durations = models.CharField(max_length=100, default="3,6,12", help_text="Enter durations separated by commas (e.g. 3,6,12)")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Product Image")
    description = models.TextField()
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class RentalOrder(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rental_duration_months = models.PositiveIntegerField(default=1)
    start_date = models.DateField(auto_now_add=True)
    delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    renewal_date = models.DateField(null=True, blank=True)
    
    # New payment and address fields
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=[('COD', 'Cash on Delivery'), ('Online', 'Online Payment')], default='COD')
    payment_status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Paid', 'Paid'), ('Failed', 'Failed')], default='Pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def calculated_total_amount(self):
        if self.total_amount is not None:
            return self.total_amount
        return self.product.price_per_month * self.rental_duration_months

    def save(self, *args, **kwargs):
        if not self.renewal_date:
            # Simple renewal date calculation: start_date + 30 days * duration
            self.renewal_date = timezone.now().date() + timedelta(days=30 * self.rental_duration_months)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

class RepairTicket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket {self.id} - {self.product.name}"

class PickupRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
    ]
    
    rental = models.OneToOneField(RentalOrder, on_delete=models.CASCADE)
    pickup_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    additional_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pickup for {self.rental.product.name} (Ticket #{self.id})"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile_no = models.CharField(max_length=20, unique=True, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    last_cleared_count = models.IntegerField(default=0)
    dismissed_notifications = models.TextField(blank=True, default='')

    def __str__(self):
        return self.user.username

    @property
    def loyalty_points(self):
        orders = RentalOrder.objects.filter(user=self.user, status__in=['Active', 'Completed'])
        return sum(o.rental_duration_months * 100 for o in orders)

    @property
    def tier(self):
        pts = self.loyalty_points
        if pts >= 1000:
            return {
                'name': 'Elite Member',
                'bg_color': '#fdfaf7',
                'color': '#b18b5e',
                'border': 'rgba(177, 139, 94, 0.3)',
                'icon': 'fa-gem'
            }
        elif pts >= 600:
            return {
                'name': 'Prestige Member',
                'bg_color': '#fcf8e3',
                'color': '#b8860b',
                'border': 'rgba(184, 134, 11, 0.2)',
                'icon': 'fa-award'
            }
        elif pts >= 300:
            return {
                'name': 'Prime Member',
                'bg_color': '#e8f4fd',
                'color': '#1d8cf8',
                'border': 'rgba(29, 140, 248, 0.2)',
                'icon': 'fa-medal'
            }
        else:
            return {
                'name': 'Explorer Member',
                'bg_color': '#f7ede2',
                'color': '#b57c50',
                'border': 'rgba(181, 124, 80, 0.2)',
                'icon': 'fa-compass'
            }

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        # OTP expires in 10 minutes
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.email} - {self.otp}"

class ContactQuery(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Query from {self.first_name} {self.last_name} ({self.email})"
