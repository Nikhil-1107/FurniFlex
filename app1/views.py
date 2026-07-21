from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Product, RentalOrder, RepairTicket, UserProfile, PasswordResetOTP, Address, ContactQuery
import random
from datetime import timedelta
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import razorpay

# Create your views here.

def home(request):
    """View for the home page featuring sample products."""
    # Get 4 sample products for the homepage
    sample_products = Product.objects.all()[:4]
    return render(request, 'home.html', {'products': sample_products})

def about(request):
    """View for the about page."""
    return render(request, 'about.html')

def contact(request):
    """View for the contact page."""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        if first_name and last_name and email and message:
            ContactQuery.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                message=message
            )
            messages.success(request, "Thank you for reaching out! Our support executives will connect with you via email within 24 hours.")
            return redirect('contact')
            
    return render(request, 'contact.html')

def custom_login(request):
    """Custom login view. Allows admins to see the login page to switch accounts."""
    if request.user.is_authenticated and not (request.user.is_staff or request.user.is_superuser):
        return redirect('home')
    
    form = AuthenticationForm()
    if request.method == 'POST':
        login_input = request.POST.get('username')
        password_input = request.POST.get('password')
        
        # Try authenticating with the provided input as username
        user = authenticate(request, username=login_input, password=password_input)
        
        # If that fails and input looks like an email, try authenticating with the username associated with that email
        if user is None and '@' in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                user = authenticate(request, username=user_obj.username, password=password_input)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            login(request, user)
            if user.is_staff or user.is_superuser:
                messages.success(request, f"Welcome back, Admin {user.username}!")
                return redirect('admin_dashboard')
            else:
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect('home')
        else:
            messages.error(request, "Invalid username/email or password. Please try again.")
            
    return render(request, 'registration/login.html', {'form': form})

def product_list(request):
    """View for the product listing page with active search and dynamic category filters."""
    from django.db.models import Q
    products = Product.objects.all()
    
    # Get active search term
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(material__icontains=query) |
            Q(color__icontains=query)
        )
        
    # Get active category selection
    category = request.GET.get('category', '').strip()
    if category and category.lower() != 'all':
        products = products.filter(category__iexact=category)
        
    # Get all distinct categories currently present in database
    categories = Product.objects.order_by('category').values_list('category', flat=True).distinct()
    
    return render(request, 'product_list.html', {
        'products': products,
        'categories': categories,
        'selected_category': category or 'All',
        'search_query': query
    })

def product_detail(request, pk):
    """View for product detail page."""
    product = Product.objects.get(pk=pk)
    # Get related products (same category, excluding current)
    related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    # Parse available durations into a list
    durations = [d.strip() for d in product.available_durations.split(',')] if product.available_durations else []
    
    # Check if the user already has an active subscription for this product
    already_rented = False
    if request.user.is_authenticated:
        already_rented = RentalOrder.objects.filter(user=request.user, product=product, status='Active').exists()
        
    return render(request, 'product_detail.html', {
        'product': product,
        'durations': durations,
        'related_products': related_products,
        'already_rented': already_rented
    })

def send_invoice_email(order):
    total_amount = order.calculated_total_amount
    discount_amount = order.discount_amount
    item_total = order.product.price_per_month * order.rental_duration_months
    subject = f"Your FurniFlex Rental Invoice - Order #{order.id}"
    
    # Render HTML content
    html_content = render_to_string('emails/invoice.html', {
        'order': order,
        'total_amount': total_amount,
        'discount_amount': discount_amount,
        'item_total': item_total,
    })
    
    text_content = strip_tags(html_content)
    
    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email]
    )
    email.attach_alternative(html_content, "text/html")
    try:
        email.send()
    except Exception as e:
        print(f"Failed to send invoice email: {e}")

def rent_product(request, pk):
    """View to handle renting a product."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_staff or request.user.is_superuser:
        messages.warning(request, "Admin users cannot rent products. Use a regular account.")
        return redirect('product_detail', pk=pk)
    product = Product.objects.get(pk=pk)
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 1))
        
        # Check if the user is a new user (has no Active or Completed orders)
        is_new_user = not RentalOrder.objects.filter(user=request.user, status__in=['Active', 'Completed']).exists()
        
        from decimal import Decimal
        monthly_price = product.price_per_month
        normal_total = monthly_price * duration
        discount = Decimal('0.00')
        if is_new_user:
            discount = monthly_price * Decimal('0.20')
            
        total = normal_total - discount
        
        order = RentalOrder.objects.create(
            user=request.user,
            product=product,
            rental_duration_months=duration,
            status='Pending',
            discount_amount=discount,
            total_amount=total
        )
        return redirect('checkout', order_id=order.id)
    
    return redirect('product_detail', pk=pk)

def checkout(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        order = RentalOrder.objects.get(pk=order_id, user=request.user, status='Pending')
    except RentalOrder.DoesNotExist:
        messages.error(request, "Rental order not found.")
        return redirect('home')
    
    addresses = Address.objects.filter(user=request.user)
    if not addresses.exists():
        try:
            profile = request.user.profile
            if profile.address:
                Address.objects.create(
                    user=request.user,
                    street_address=profile.address,
                    city=profile.city or "",
                    state="",
                    pincode=profile.pincode or "",
                    is_default=True
                )
                addresses = Address.objects.filter(user=request.user)
        except UserProfile.DoesNotExist:
            pass
    
    # We will charge the calculated total amount
    monthly_amount = order.product.price_per_month
    total_amount = order.calculated_total_amount
    discount_amount = order.discount_amount
    
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        new_address = request.POST.get('new_address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')
        
        # Determine the address
        if address_id == 'new':
            if not (new_address and city and state and pincode):
                messages.error(request, "Please fill in all address fields.")
                return redirect('checkout', order_id=order.id)
            addr = Address.objects.create(
                user=request.user,
                street_address=new_address,
                city=city,
                state=state,
                pincode=pincode
            )
        else:
            try:
                addr = Address.objects.get(pk=address_id, user=request.user)
            except Address.DoesNotExist:
                messages.error(request, "Invalid address selected.")
                return redirect('checkout', order_id=order.id)
        
        order.address = addr
        payment_method = request.POST.get('payment_method')
        order.payment_method = payment_method
        order.save()
        
        if payment_method == 'COD':
            order.status = 'Active'
            order.payment_status = 'Pending'
            order.save()
            # Decrement stock
            if order.product.stock > 0:
                order.product.stock -= 1
                order.product.save()
            
            # Send premium email invoice
            send_invoice_email(order)
            
            messages.success(request, f"Rental confirmed! Order will be delivered to {addr.street_address}, {addr.city}.")
            return redirect('my_rentals')
            
        elif payment_method == 'Online':
            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create(data={
                'amount': int(total_amount * 100),
                'currency': 'INR',
                'payment_capture': 1
            })
            
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            context = {
                'order': order,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': total_amount,
                'amount_paise': int(total_amount * 100),
                'user_profile': request.user.profile if hasattr(request.user, 'profile') else None,
                'address': addr
            }
            return render(request, 'razorpay_payment.html', context)
            
    # GET request
    context = {
        'order': order,
        'addresses': addresses,
        'monthly_amount': monthly_amount,
        'discount_amount': discount_amount,
        'total_amount': total_amount,
    }
    return render(request, 'checkout.html', context)

@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')
        
        try:
            order = RentalOrder.objects.get(razorpay_order_id=order_id)
        except RentalOrder.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('home')
        
        # Verify the signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
            # Signature matches!
            order.status = 'Active'
            order.payment_status = 'Paid'
            order.razorpay_payment_id = payment_id
            order.razorpay_signature = signature
            order.save()
            
            # Decrement product stock
            if order.product.stock > 0:
                order.product.stock -= 1
                order.product.save()
                
            # Send premium email invoice
            send_invoice_email(order)
                
            messages.success(request, "Payment successful! Your rental is active.")
            return redirect('my_rentals')
        except Exception as e:
            order.payment_status = 'Failed'
            order.save()
            messages.error(request, "Payment verification failed. Please contact support.")
            return redirect('my_rentals')
            
    return redirect('home')

def my_rentals(request):
    """View for user's active rentals."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_dashboard')
    rentals = RentalOrder.objects.filter(user=request.user, status__in=['Active', 'Completed']).order_by('-created_at')
    return render(request, 'my_rentals.html', {'rentals': rentals})

from .forms import UserRegistrationForm, UserProfileForm

def profile(request):
    """View for user profile management."""
    if not request.user.is_authenticated:
        return redirect('login')
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_dashboard')
    
    # Get or create profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            # Get the full international number from the hidden field
            full_mobile = request.POST.get('full_mobile')
            # Custom save to handle full_mobile if provided
            instance = form.save(commit=False)
            if full_mobile:
                instance.mobile_no = full_mobile
            instance.save()
            
            # Update user email as well
            request.user.email = request.POST.get('email')
            request.user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
        # Pre-fill email from User model
        form.fields['email'].initial = request.user.email
        
    # Calculate real-time active rentals and loyalty points
    active_rentals_count = RentalOrder.objects.filter(user=request.user, status='Active').count()
    all_orders = RentalOrder.objects.filter(user=request.user, status__in=['Active', 'Completed'])
    loyalty_points = sum(o.rental_duration_months * 100 for o in all_orders)
        
    return render(request, 'profile.html', {
        'form': form,
        'profile': profile,
        'active_rentals_count': active_rentals_count,
        'loyalty_points': loyalty_points
    })

def delete_account(request):
    """View to handle account deletion."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, "Your account has been permanently deleted. We're sorry to see you go!")
        return redirect('home')
    
    return redirect('profile')

def support_tickets(request):
    """View for user's repair tickets."""
    if not request.user.is_authenticated:
        return redirect('login')
    tickets = RepairTicket.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'support_tickets.html', {'tickets': tickets})

def create_repair_ticket(request, rental_id):
    """View to create a repair ticket for a specific rental."""
    if not request.user.is_authenticated:
        return redirect('login')
    
    rental = RentalOrder.objects.get(pk=rental_id)
    if request.method == 'POST':
        description = request.POST.get('description')
        RepairTicket.objects.create(
            user=request.user,
            product=rental.product,
            description=description
        )
        messages.success(request, "Repair ticket submitted successfully!")
        return redirect('support_tickets')
    
    return render(request, 'create_repair_ticket.html', {'rental': rental})

def register(request):
    """View for user registration."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Get the full international number from the hidden field
            full_mobile = request.POST.get('full_mobile')
            user = form.save(full_mobile=full_mobile)
            login(request, user)
            messages.success(request, f"Welcome to FurniFlex, {user.username}!")
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            
            # Delete any existing OTPs for this user
            PasswordResetOTP.objects.filter(user=user).delete()
            
            # Create new OTP
            PasswordResetOTP.objects.create(user=user, otp=otp)
            
            # Send Email
            subject = 'Your FurniFlex Password Reset OTP'
            message = f'Hi {user.username},\n\nYour OTP for password reset is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nRegards,\nTeam FurniFlex'
            email_from = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            send_mail(subject, message, email_from, recipient_list)
            
            request.session['reset_email'] = email
            messages.success(request, 'OTP has been sent to your email.')
            return redirect('verify_otp')
            
        except User.DoesNotExist:
            messages.error(request, 'No user found with this email address.')
            
    return render(request, 'registration/forgot_password.html')

def verify_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
        
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        try:
            user = User.objects.get(email=email)
            otp_obj = PasswordResetOTP.objects.filter(user=user, otp=otp_input).last()
            
            if otp_obj and not otp_obj.is_expired():
                otp_obj.is_verified = True
                otp_obj.save()
                messages.success(request, 'OTP verified successfully. Please set your new password.')
                return redirect('reset_password')
            else:
                messages.error(request, 'Invalid or expired OTP.')
        except User.DoesNotExist:
            return redirect('forgot_password')
            
    return render(request, 'registration/verify_otp.html', {'email': email})

def reset_password(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
        
    try:
        user = User.objects.get(email=email)
        otp_obj = PasswordResetOTP.objects.filter(user=user, is_verified=True).last()
        
        if not otp_obj:
            return redirect('verify_otp')
            
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            if password == confirm_password:
                user.set_password(password)
                user.save()
                # Clean up OTP
                otp_obj.delete()
                del request.session['reset_email']
                messages.success(request, 'Password reset successful. Please login with your new password.')
                return redirect('login')
            else:
                messages.error(request, 'Passwords do not match.')
    except User.DoesNotExist:
        return redirect('forgot_password')
        
    return render(request, 'registration/reset_password.html')

@csrf_exempt
def renewal_payment_success(request):
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')
        
        # Retrieve details from POST (preferred) or session (fallback)
        rental_id = request.POST.get('rental_id') or request.session.get('renewal_order_id')
        duration_val = request.POST.get('duration') or request.session.get('renewal_duration')
        
        if not rental_id or not duration_val:
            messages.error(request, "Invalid renewal transaction.")
            return redirect('my_rentals')
            
        try:
            rental = RentalOrder.objects.get(pk=int(rental_id))
        except (RentalOrder.DoesNotExist, ValueError):
            messages.error(request, "Original rental order not found.")
            return redirect('my_rentals')
            
        duration = int(duration_val)
        
        # Verify Razorpay signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
            
            # Signature matches!
            # Extend subscription
            rental.rental_duration_months += duration
            rental.renewal_date = rental.renewal_date + timedelta(days=30 * duration)
            rental.payment_method = 'Online'
            rental.payment_status = 'Paid'
            rental.razorpay_payment_id = payment_id
            rental.razorpay_signature = signature
            rental.save()
            
            # Clean up session keys if they exist
            if 'renewal_order_id' in request.session:
                del request.session['renewal_order_id']
            if 'renewal_duration' in request.session:
                del request.session['renewal_duration']
            if 'renewal_razorpay_order_id' in request.session:
                del request.session['renewal_razorpay_order_id']
            
            # Send premium email invoice
            send_invoice_email(rental)
            
            messages.success(request, f"Payment successful! Subscription successfully renewed for an additional {duration} months!")
            return redirect('my_rentals')
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect('my_rentals')
            
    return redirect('home')

def renew_rental(request, rental_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    rental = get_object_or_404(RentalOrder, pk=rental_id, user=request.user)
    
    if request.method == 'POST':
        duration = int(request.POST.get('duration', 3))
        payment_method = request.POST.get('payment_method', 'Online')
        amount = rental.product.price_per_month * duration
        
        if payment_method != 'Online':
            messages.error(request, "Only online payments are accepted for subscription renewals.")
            return redirect('my_rentals')
            
        # Initialize online payment
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            razorpay_order = client.order.create(data={
                'amount': int(amount * 100),
                'currency': 'INR',
                'payment_capture': 1
            })
            
            # Store details in session
            request.session['renewal_order_id'] = rental.id
            request.session['renewal_duration'] = duration
            request.session['renewal_razorpay_order_id'] = razorpay_order['id']
            
            context = {
                'order': rental,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': amount,
                'amount_paise': int(amount * 100),
                'user_profile': request.user.profile if hasattr(request.user, 'profile') else None,
                'address': rental.address,
                'is_renewal': True,
                'duration': duration
            }
            return render(request, 'razorpay_payment.html', context)
        except Exception as e:
            messages.error(request, f"Error initializing online payment: {str(e)}")
            return redirect('my_rentals')
                
    return redirect('my_rentals')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def clear_notifications(request):
    if request.user.is_authenticated:
        count = request.POST.get('count', 0)
        try:
            count = int(count)
        except ValueError:
            count = 0
        
        # Persist to database UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.last_cleared_count = count
        profile.save()
        
        request.session['last_cleared_count'] = count
        request.session.modified = True
        return JsonResponse({'status': 'success', 'cleared_count': count})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

@csrf_exempt
def clear_all_notifications(request):
    if request.user.is_authenticated:
        from furniflex.context_processors import user_notifications
        context = user_notifications(request)
        current_notifications = context.get('user_notifications', [])
        
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        dismissed_str = profile.dismissed_notifications or ''
        dismissed_keys = set(k.strip() for k in dismissed_str.split(',') if k.strip())
        
        for n in current_notifications:
            dismissed_keys.add(n['key'])
            
        profile.dismissed_notifications = ','.join(dismissed_keys)
        profile.last_cleared_count = 0
        profile.save()
        
        if 'last_cleared_count' in request.session:
            request.session['last_cleared_count'] = 0
            request.session.modified = True
            
        return JsonResponse({'status': 'success', 'message': 'All notifications cleared'})
    return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
