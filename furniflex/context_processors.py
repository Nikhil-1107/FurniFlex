from django.utils import timezone
from django.urls import reverse
from app1.models import RentalOrder, RepairTicket, UserProfile

def user_notifications(request):
    notifications = []
    unread_count = 0
    
    if request.user.is_authenticated and not request.user.is_staff and not request.user.is_superuser:
        # Fetch all orders to build alerts and calculate points
        all_orders = RentalOrder.objects.filter(user=request.user)
        active_rentals = all_orders.filter(status='Active')
        
        # 1. Points Earned Notifications for each active rental order
        for rental in all_orders.filter(status='Active'):
            pts_earned = rental.rental_duration_months * 100
            notifications.append({
                'type': 'points_earned',
                'key': f"points_earned_{rental.id}",
                'title': 'Points Earned!',
                'text': f"You earned <strong>{pts_earned} Loyalty Points</strong> for renting <strong>{rental.product.name}</strong>!",
                'link': reverse('profile'),
                'icon': 'fa-circle-plus',
                'color': 'text-success'
            })

        # 2. Expiry & Renewal Alerts
        for rental in active_rentals:
            if rental.renewal_date:
                remaining_days = (rental.renewal_date - timezone.now().date()).days
                if remaining_days <= 7 and remaining_days >= 0:
                    notifications.append({
                        'type': 'renewal_warning',
                        'key': f"renewal_warning_{rental.id}_{rental.renewal_date}",
                        'title': 'Rental Expiring Soon',
                        'text': f"Your rental for <strong>{rental.product.name}</strong> expires in {remaining_days} days! Renew now.",
                        'link': reverse('my_rentals'),
                        'icon': 'fa-hourglass-half',
                        'color': 'text-warning'
                    })
                elif remaining_days < 0:
                    notifications.append({
                        'type': 'renewal_overdue',
                        'key': f"renewal_overdue_{rental.id}_{rental.renewal_date}",
                        'title': 'Rental Overdue',
                        'text': f"Your rental for <strong>{rental.product.name}</strong> expired {abs(remaining_days)} days ago! Please renew or schedule a return.",
                        'link': reverse('my_rentals'),
                        'icon': 'fa-circle-exclamation',
                        'color': 'text-danger'
                    })

        # 3. Fetch repair ticket updates
        user_tickets = RepairTicket.objects.filter(user=request.user)
        for ticket in user_tickets:
            if ticket.status == 'Open':
                notifications.append({
                    'type': 'ticket_open',
                    'key': f"ticket_open_{ticket.id}_{ticket.status}",
                    'title': 'Ticket Registered',
                    'text': f"Support Ticket #{ticket.id} is registered for <strong>{ticket.product.name}</strong>.",
                    'link': reverse('support_tickets'),
                    'icon': 'fa-ticket',
                    'color': 'text-info'
                })
            elif ticket.status == 'In Progress':
                notifications.append({
                    'type': 'ticket_progress',
                    'key': f"ticket_progress_{ticket.id}_{ticket.status}",
                    'title': 'Ticket In Progress',
                    'text': f"Support agent is dispatched for your <strong>{ticket.product.name}</strong>.",
                    'link': reverse('support_tickets'),
                    'icon': 'fa-screwdriver-wrench',
                    'color': 'text-primary'
                })
            elif ticket.status == 'Resolved':
                notifications.append({
                    'type': 'ticket_resolved',
                    'key': f"ticket_resolved_{ticket.id}_{ticket.status}",
                    'title': 'Ticket Resolved',
                    'text': f"Support Ticket #{ticket.id} for <strong>{ticket.product.name}</strong> has been resolved.",
                    'link': reverse('support_tickets'),
                    'icon': 'fa-circle-check',
                    'color': 'text-success'
                })

        # 4. Calculate total loyalty points reward alert
        loyalty_points = sum(o.rental_duration_months * 100 for o in all_orders.filter(status__in=['Active', 'Completed']))
        if loyalty_points > 0:
            notifications.append({
                'type': 'loyalty_alert',
                'key': f"loyalty_alert_{loyalty_points}",
                'title': 'Loyalty Reward Active',
                'text': f"You have <strong>{loyalty_points} Loyalty Points</strong> available! Keep renting to earn more.",
                'link': reverse('profile'),
                'icon': 'fa-gem',
                'color': 'text-primary'
            })

        # 5. Standard welcome alert if notifications list is empty
        if not notifications:
            notifications.append({
                'type': 'general',
                'key': 'general_welcome',
                'title': 'Welcome to FurniFlex',
                'text': 'Rent beautiful, luxury designer collections today. Browse our trending catalogue!',
                'link': reverse('home'),
                'icon': 'fa-couch',
                'color': 'text-primary'
            })

        # Filter out dismissed notifications
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        dismissed_str = profile.dismissed_notifications or ''
        dismissed_keys = set(k.strip() for k in dismissed_str.split(',') if k.strip())
        
        filtered_notifications = [n for n in notifications if n['key'] not in dismissed_keys]

        # Dynamic Database & Session-Based AJAX Unread Calculation:
        # Calculates new notifications persistently by reading from the user profile in the database
        current_count = len(filtered_notifications)
        last_cleared = profile.last_cleared_count
        unread_count = max(0, current_count - last_cleared)
        notifications = filtered_notifications

    return {
        'user_notifications': notifications,
        'notifications_unread_count': unread_count
    }
