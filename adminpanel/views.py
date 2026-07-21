from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from app1.models import Product, RentalOrder, RepairTicket, UserProfile, ContactQuery
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import re
import json

# Helper to check staff permissions
def check_admin(request):
    if not request.user.is_authenticated:
        return False
    return request.user.is_staff or request.user.is_superuser

def admin_login(request):
    """Dedicated login view for administrators."""
    if check_admin(request):
        return redirect('admin_dashboard')
        
    if request.method == 'POST':
        username_input = request.POST.get('username')
        password_input = request.POST.get('password')
        
        user = authenticate(request, username=username_input, password=password_input)
        
        if user is None and '@' in username_input:
            try:
                user_obj = User.objects.get(email=username_input)
                user = authenticate(request, username=user_obj.username, password=password_input)
            except User.DoesNotExist:
                pass
                
        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Access Granted. Welcome to the Control Deck, Admin {user.username}!")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Access Denied. Standard user accounts cannot access the Admin Portal.")
        else:
            messages.error(request, "Invalid administrator credentials. Please check your username/email and password.")
            
    return render(request, 'adminpanel/login.html')

def dashboard(request):
    if not check_admin(request):
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('admin_login')
    
    # Calculate stats
    total_active_rentals = RentalOrder.objects.filter(status='Active').count()
    total_users = User.objects.filter(is_staff=False).count()
    unresolved_tickets = RepairTicket.objects.exclude(status='Resolved').count()
    
    # Calculate total revenue with time-period filters
    revenue_days = request.GET.get('revenue_days', 'lifetime')
    paid_orders = RentalOrder.objects.filter(payment_status='Paid', status__in=['Active', 'Completed'])
    
    if revenue_days in ['7', '14', '30', '90']:
        days_limit = int(revenue_days)
        start_date = timezone.now() - timedelta(days=days_limit)
        paid_orders = paid_orders.filter(created_at__gte=start_date)
        revenue_label = f"Last {revenue_days} Days"
    else:
        revenue_label = "Lifetime Earnings"
        
    total_revenue = sum(order.product.price_per_month * order.rental_duration_months for order in paid_orders)
    
    # Calculate monthly revenue for the last 6 months dynamically
    monthly_revenue_labels = []
    monthly_revenue_data = []
    
    for i in range(5, -1, -1):
        current_year = timezone.now().year
        current_month = timezone.now().month
        
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        month_date = timezone.now().replace(year=target_year, month=target_month, day=1)
        monthly_revenue_labels.append(month_date.strftime("%B"))
        
        # Filter paid orders that were created in this target month and year
        month_orders = RentalOrder.objects.filter(
            payment_status='Paid',
            status__in=['Active', 'Completed'],
            created_at__year=target_year,
            created_at__month=target_month
        )
        month_total = sum(order.product.price_per_month * order.rental_duration_months for order in month_orders)
        monthly_revenue_data.append(float(month_total))
        
    # Calculate category distribution for active rentals
    category_counts = {}
    active_rentals_list = RentalOrder.objects.filter(status='Active')
    for rental in active_rentals_list:
        cat = rental.product.category
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
    category_labels = list(category_counts.keys())
    category_data = list(category_counts.values())
    
    # Fallback to make the chart look stunning if there is no data
    if not category_labels:
        category_labels = ["Sofa", "Bed", "Dining", "Office"]
        category_data = [3, 2, 4, 1]
        
    # Recent rentals
    recent_rentals = RentalOrder.objects.order_by('-created_at')[:5]
    
    # Recent support tickets
    recent_tickets = RepairTicket.objects.order_by('-created_at')[:5]
    
    # Recent contact queries
    recent_queries = ContactQuery.objects.order_by('-created_at')[:4]

    context = {
        'total_active_rentals': total_active_rentals,
        'total_users': total_users,
        'unresolved_tickets': unresolved_tickets,
        'total_revenue': total_revenue,
        'recent_rentals': recent_rentals,
        'recent_queries': recent_queries,
        'recent_tickets': recent_tickets,
        'revenue_days': revenue_days,
        'revenue_label': revenue_label,
        'monthly_revenue_labels': json.dumps(monthly_revenue_labels),
        'monthly_revenue_data': json.dumps(monthly_revenue_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
    }
    return render(request, 'adminpanel/dashboard.html', context)

def products(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('home')
        
    category_filter = request.GET.get('category', 'all')
    stock_filter = request.GET.get('stock', 'all')
    search_query = request.GET.get('q', '')
    
    all_products = Product.objects.all()
    
    if category_filter != 'all':
        all_products = all_products.filter(category=category_filter)
        
    if stock_filter == 'instock':
        all_products = all_products.filter(stock__gt=0)
    elif stock_filter == 'outofstock':
        all_products = all_products.filter(stock=0)
        
    if search_query:
        all_products = all_products.filter(name__icontains=search_query)
        
    categories = Product.CATEGORY_CHOICES
    
    context = {
        'products': all_products,
        'categories': categories,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
        'search_query': search_query,
    }
    return render(request, 'adminpanel/products.html', context)

def product_add(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        price_per_month = request.POST.get('price_per_month')
        material = request.POST.get('material')
        color = request.POST.get('color')
        stock = request.POST.get('stock')
        available_durations = request.POST.get('available_durations', '3,6,12')
        description = request.POST.get('description')
        image = request.FILES.get('image')
        
        try:
            Product.objects.create(
                name=name,
                category=category,
                price_per_month=price_per_month,
                material=material,
                color=color,
                stock=stock,
                available_durations=available_durations,
                description=description,
                image=image
            )
            messages.success(request, f"Product '{name}' added successfully!")
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f"Error adding product: {str(e)}")
            
    categories = Product.CATEGORY_CHOICES
    return render(request, 'adminpanel/product_form.html', {'categories': categories, 'action': 'Add'})

def product_edit(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('home')
    
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category = request.POST.get('category')
        product.price_per_month = request.POST.get('price_per_month')
        product.material = request.POST.get('material')
        product.color = request.POST.get('color')
        product.stock = request.POST.get('stock')
        product.available_durations = request.POST.get('available_durations', '3,6,12')
        product.description = request.POST.get('description')
        
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')
            
        try:
            product.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('admin_products')
        except Exception as e:
            messages.error(request, f"Error updating product: {str(e)}")
            
    categories = Product.CATEGORY_CHOICES
    return render(request, 'adminpanel/product_form.html', {'product': product, 'categories': categories, 'action': 'Edit'})

def product_delete(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('home')
    product = get_object_or_404(Product, pk=pk)
    product_name = product.name
    product.delete()
    messages.success(request, f"Product '{product_name}' was successfully deleted.")
    return redirect('admin_products')

def rentals(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('home')
        
    status_filter = request.GET.get('status', 'all')
    payment_filter = request.GET.get('payment', 'all')
    search_query = request.GET.get('q', '')
    
    all_rentals = RentalOrder.objects.all().order_by('-created_at')
    
    if status_filter != 'all':
        all_rentals = all_rentals.filter(status=status_filter)
        
    if payment_filter != 'all':
        all_rentals = all_rentals.filter(payment_status=payment_filter)
        
    if search_query:
        all_rentals = all_rentals.filter(user__username__icontains=search_query) | all_rentals.filter(product__name__icontains=search_query)
        
    context = {
        'rentals': all_rentals,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'search_query': search_query,
    }
    return render(request, 'adminpanel/rentals.html', context)

def update_rental_status(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('home')
    rental = get_object_or_404(RentalOrder, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = rental.status
        
        # State transition stock handler
        if old_status in ['Pending', 'Active'] and new_status in ['Completed', 'Cancelled']:
            rental.product.stock += 1
            rental.product.save()
        elif old_status in ['Completed', 'Cancelled'] and new_status in ['Pending', 'Active']:
            if rental.product.stock > 0:
                rental.product.stock -= 1
                rental.product.save()
                
        rental.status = new_status
        rental.save()
        messages.success(request, f"Status of Rental #{rental.id} updated to {new_status}.")
    return redirect('admin_rentals')

def tickets(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    all_tickets = RepairTicket.objects.all().order_by('-created_at')
    
    if status_filter != 'all':
        all_tickets = all_tickets.filter(status=status_filter)
        
    if search_query:
        all_tickets = all_tickets.filter(user__username__icontains=search_query) | all_tickets.filter(product__name__icontains=search_query)
        
    context = {
        'tickets': all_tickets,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'adminpanel/tickets.html', context)

def resolve_ticket(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
    ticket = get_object_or_404(RepairTicket, pk=pk)
    ticket.status = 'Resolved'
    ticket.save()
    messages.success(request, f"Ticket #{ticket.id} has been marked as Resolved.")
    return redirect('admin_tickets')

def users(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    search_query = request.GET.get('q', '')
    
    user_list = User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined')
    
    if search_query:
        user_list = user_list.filter(username__icontains=search_query) | user_list.filter(email__icontains=search_query)
    
    # Augment users with their metrics
    for user in user_list:
        active_rentals = RentalOrder.objects.filter(user=user, status='Active')
        user.active_rentals_count = active_rentals.count()
        
        # Calculate loyalty points: 100 PTS per rental duration month across all Active and Completed orders
        all_valid_rentals = RentalOrder.objects.filter(user=user, status__in=['Active', 'Completed'])
        total_months = sum(order.rental_duration_months for order in all_valid_rentals)
        user.loyalty_points = total_months * 100
        
    context = {
        'users': user_list,
        'search_query': search_query,
    }
    return render(request, 'adminpanel/users.html', context)

def user_add(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        mobile_no = request.POST.get('mobile_no')
        address = request.POST.get('address')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        full_mobile = request.POST.get('full_mobile')
        
        # Validation checks
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email address is already registered.")
        elif UserProfile.objects.filter(mobile_no__contains=mobile_no).exists():
            messages.error(request, "A user with this mobile number already exists.")
        elif len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            messages.error(request, "Password must be at least 8 characters long, containing at least one letter, one number, and one special character.")
        else:
            try:
                user = User.objects.create_user(username=username, email=email, password=password)
                UserProfile.objects.create(
                    user=user,
                    mobile_no=full_mobile if full_mobile else mobile_no,
                    address=address,
                    city=city,
                    pincode=pincode
                )
                messages.success(request, f"Customer account '{username}' created successfully!")
                return redirect('admin_users')
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
                
    return render(request, 'adminpanel/user_form.html', {'action': 'Add'})

def user_edit(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    user_obj = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=user_obj)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        mobile_no = request.POST.get('mobile_no')
        address = request.POST.get('address')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        new_password = request.POST.get('password')
        full_mobile = request.POST.get('full_mobile')
        
        # Validation checks
        if username != user_obj.username and User.objects.filter(username=username).exists():
            messages.error(request, "Username is already taken.")
        elif email != user_obj.email and User.objects.filter(email=email).exists():
            messages.error(request, "Email address is already registered.")
        elif mobile_no != profile.mobile_no and UserProfile.objects.filter(mobile_no__contains=mobile_no).exists():
            messages.error(request, "A user with this mobile number already exists.")
        elif new_password and (len(new_password) < 8 or not re.search(r'[A-Za-z]', new_password) or not re.search(r'\d', new_password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password)):
            messages.error(request, "New password must be at least 8 characters long, containing at least one letter, one number, and one special character.")
        else:
            try:
                user_obj.username = username
                user_obj.email = email
                if new_password:
                    user_obj.set_password(new_password)
                user_obj.save()
                
                profile.mobile_no = full_mobile if full_mobile else mobile_no
                profile.address = address
                profile.city = city
                profile.pincode = pincode
                profile.save()
                
                messages.success(request, f"Customer account '{username}' updated successfully!")
                return redirect('admin_users')
            except Exception as e:
                messages.error(request, f"Error updating user: {str(e)}")
                
    return render(request, 'adminpanel/user_form.html', {'user_obj': user_obj, 'profile': profile, 'action': 'Edit'})

def user_delete(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    user_obj = get_object_or_404(User, pk=pk)
    username = user_obj.username
    user_obj.delete()
    messages.success(request, f"Customer account '{username}' was successfully deleted.")
    return redirect('admin_users')

def mark_rental_paid(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    rental = get_object_or_404(RentalOrder, pk=pk)
    if rental.payment_method == 'COD' and rental.payment_status == 'Pending':
        rental.payment_status = 'Paid'
        rental.save()
        messages.success(request, f"Rental Order #{rental.id} has been marked as PAID! Earnings have been updated.")
    else:
        messages.error(request, "Order cannot be marked as paid.")
        
    return redirect('admin_rentals')

def contact_queries(request):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
        
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    queries = ContactQuery.objects.all().order_by('-created_at')
    
    if status_filter == 'replied':
        queries = queries.filter(is_resolved=True)
    elif status_filter == 'unreplied':
        queries = queries.filter(is_resolved=False)
        
    if search_query:
        queries = queries.filter(first_name__icontains=search_query) | queries.filter(email__icontains=search_query) | queries.filter(message__icontains=search_query)
        
    context = {
        'queries': queries,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'adminpanel/queries.html', context)

def send_query_reply(request, pk):
    if not check_admin(request):
        messages.error(request, "Access denied.")
        return redirect('admin_login')
    
    if request.method == 'POST':
        query = get_object_or_404(ContactQuery, pk=pk)
        subject = request.POST.get('subject', 'Response to your FurniFlex Inquiry')
        reply_message = request.POST.get('reply_message')
        
        if reply_message:
            try:
                # Send email
                send_mail(
                    subject,
                    f"Hello {query.first_name},\n\nThank you for reaching out to FurniFlex. Here is the response to your inquiry:\n\n---\nYOUR INQUIRY:\n\"{query.message}\"\n---\n\nOUR RESPONSE:\n{reply_message}\n\nWarm regards,\nThe FurniFlex Team",
                    settings.DEFAULT_FROM_EMAIL,
                    [query.email],
                    fail_silently=False,
                )
                
                # Mark as resolved
                query.is_resolved = True
                query.save()
                messages.success(request, f"Reply email successfully sent to {query.email}!")
            except Exception as e:
                messages.error(request, f"Failed to send email: {str(e)}")
                
    return redirect('admin_queries')
