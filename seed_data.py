import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'furniflex.settings')
django.setup()

from app1.models import Product

def create_sample_products():
    products = [
        {
            'name': 'Velvet Lounge Sofa',
            'category': 'Sofa',
            'price_per_month': 49.99,
            'description': 'A luxurious and comfortable velvet sofa, perfect for your living room.'
        },
        {
            'name': 'Queen Size Bed',
            'category': 'Bed',
            'price_per_month': 75.00,
            'description': 'Modern minimalist bed frame with a comfortable premium mattress.'
        },
        {
            'name': 'Modern Dining Set',
            'category': 'Dining',
            'price_per_month': 59.00,
            'description': 'A sleek dining table with 4 chairs, ideal for family dinners.'
        },
        {
            'name': 'Ergonomic Office Chair',
            'category': 'Office',
            'price_per_month': 25.00,
            'description': 'Support your back with our premium ergonomic office chair.'
        }
    ]

    for p_data in products:
        Product.objects.get_or_create(
            name=p_data['name'],
            defaults={
                'category': p_data['category'],
                'price_per_month': p_data['price_per_month'],
                'description': p_data['description'],
                'available': True
            }
        )
    print("Sample products created successfully!")

if __name__ == '__main__':
    create_sample_products()
