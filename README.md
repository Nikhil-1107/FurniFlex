# FurniFlex

FurniFlex is a modern furniture rental platform built with Django. It allows users to browse furniture products, place rental orders, manage accounts, and interact with an admin dashboard for product and order management.

## Project Context

FurniFlex is designed for customers who want stylish, flexible furniture solutions without the long-term commitment of purchasing. The platform combines e-commerce functionality with a rental experience, making it easy to explore products, reserve items, and complete payments.

### Core Goals
- Provide a smooth furniture rental experience for customers
- Showcase premium furniture products with an elegant storefront
- Support order management, payments, and user accounts
- Offer an admin panel for managing inventory and rentals

## Key Features
- User registration and login
- Product listing and detail pages
- Rental order placement
- Payment integration with Razorpay
- Contact and support ticket handling
- Admin dashboard for operations and management
- Responsive design for desktop and mobile users

## Tech Stack
- Python
- Django
- SQLite (development)
- Bootstrap 5
- HTML/CSS/JavaScript
- Pillow for image handling
- Razorpay for payments

## Project Structure
- `app1/` – main storefront logic, models, views, forms, and URLs
- `adminpanel/` – admin-side features and dashboard
- `templates/` – HTML templates for the website
- `static/` – CSS, JS, and images
- `media/` – uploaded product and user images

## Theme and Colors

FurniFlex uses a warm, premium, modern visual style inspired by elegant interiors and premium furniture brands.

### Visual Style
- Minimal and refined
- Sophisticated and premium
- Clean layout with strong typography
- Soft shadows and smooth transitions

### Color Palette
- Primary: `#b18b5e` – warm earthy brown
- Secondary: `#2c2c2c` – deep charcoal
- Accent: `#f4e9dc` – cream/beige
- Dark Background: `#1a1a1a`
- Light Background: `#fdfaf7`
- Hover Brown: `#8e6f4a`

### Typography
- Headings: Playfair Display
- Body text: Outfit

## Getting Started

### Prerequisites
- Python 3.x
- pip

### Installation
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Notes
This project is suitable for a furniture rental business, home staging, interior design services, or premium lifestyle e-commerce experiences.
