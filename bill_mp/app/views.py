from django.shortcuts import render ,redirect 
from django.contrib.auth import  authenticate, login
from django.contrib import messages
from .models import User , Customer ,Staff
from django.core.mail import send_mail
from django.conf import settings
import random
from django.contrib.auth.hashers import make_password



def home(request):
    return render(request, 'home.html')

def features_view(request):
    return render(request, 'features.html')

def about_view(request):
    return render(request, 'about.html')

def register(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')

        customer_id = request.POST.get('customer_id')
        department = request.POST.get('department')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('customer_register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect('customer_register')

        if User.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number already registered")
            return redirect('register')

        # Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            phone=phone,
            password=password,
            first_name=name,
            role=role
        )

        # ---------------- CUSTOMER ----------------
        if role == 'CUSTOMER':
            if Customer.objects.filter(customer_id=customer_id).exists():
                messages.error(request, "Customer ID already exists")
                return redirect('register')

            Customer.objects.create(
                user=user,
                customer_id=customer_id,
                address="",
                connection_type="ELECTRICITY"  # default (can change later)
            )

            login(request, user)
            return redirect('customer_login')

        # ---------------- STAFF ----------------
        if role == 'STAFF':
            Staff.objects.create(
                user=user,
                utility_type=department,  # ✅ FROM DROPDOWN
                is_approved=False         # ✅ admin approval
            )

            messages.success(
                request,
                "Staff account created. Please wait for admin approval."
            )
            return redirect('customer_login')

    return render(request, 'consumer/register.html')

def customer_login(request):

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        # IMPORTANT:
        # This works only if username == email in your User model
        user = authenticate(
            request,
            username=email,
            password=password
        )

        if user is None:
            messages.error(request, "Invalid email or password")
            return redirect('customer_login')
        
        User.objects.filter(is_active=False).update(is_active=True)

        print("All users activated")
        # ---------------- STAFF CHECK ----------------
        if user.role == 'STAFF':

            try:
                staff = user.staff_profile
            except Staff.DoesNotExist:
                messages.error(request, "Staff profile not found")
                return redirect('customer_login')

            if not staff.is_approved:
                messages.error(
                    request,
                    "Your staff account is pending admin approval."
                )
                return redirect('customer_login')

            if not staff.is_active:
                messages.error(
                    request,
                    "Your staff account is deactivated."
                )
                return redirect('customer_login')

        login(request, user)

        # ---------------- REDIRECT BASED ON ROLE ----------------
        if user.role == 'STAFF':
            return redirect('staff_dashboard')

        elif user.role == 'CUSTOMER':
            return redirect('customer_dashboard')

        elif user.role == 'ADMIN':
            return redirect('staff_dashboard')  # or admin dashboard

        else:
            return redirect('home')

    return render(request, 'consumer/login.html')
import random
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect

def forgot_password(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier")

        user = User.objects.filter(email=identifier, role="CUSTOMER").first()

        if not user:
            cust = Customer.objects.filter(phone=identifier).first()
            if cust:
                user = cust.user

        if not user:
            messages.error(request, "User not found")
            return redirect("forgot_password")

        otp = random.randint(100000, 999999)

        request.session["reset_user"] = user.id
        request.session["reset_otp"] = str(otp)

        send_mail(
            subject="Smart Utility OTP Verification",
            message=f"Your OTP for password reset is: {otp}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        messages.success(request, "OTP sent to registered email")
        return redirect("verify_otp")

    return render(request, "consumer/forgot.html")

def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        session_otp = request.session.get("reset_otp")

        if entered_otp == session_otp:
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP")
            return redirect("verify_otp")

    return render(request, "consumer/verify.html")

def reset_password(request):
    if request.method == "POST":
        password = request.POST.get("new_password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("reset_password")

        user_id = request.session.get("reset_user")
        user = User.objects.get(id=user_id)
        user.password = make_password(password)
        user.save()

        request.session.flush()
        messages.success(request, "Password reset successful")
        return redirect("customer_login")

    return render(request, "consumer/reset.html")

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum
from django.utils.timezone import now
from django.db.models import Q, Sum, Count
from .models import Customer, Bill, Payment 
from django.contrib.auth import authenticate, login as auth_login



@login_required
def customer_dashboard(request):
    user = request.user

    # Ensure only customers access dashboard
    if user.role != 'CUSTOMER':
        return redirect('customer_login')

    # ✅ FIX 1: Correct variable naming
    try:
        customer_profile = Customer.objects.get(user=user)
    except Customer.DoesNotExist:
        return redirect('customer_login')

    # ✅ Unpaid bills
    unpaid_bills = Bill.objects.filter(
        customer=customer_profile,
        is_paid=False
    )

    # ✅ Total due
    total_due = unpaid_bills.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # ✅ Usage calculations (FIXED FIELD NAMES)
    electricity_usage = Bill.objects.filter(
        customer=customer_profile,
        connection_type='ELECTRICITY'
    ).aggregate(total=Sum('units_consumed'))['total'] or 0

    water_usage = Bill.objects.filter(
        customer=customer_profile,
        connection_type='WATER'
    ).aggregate(total=Sum('units_consumed'))['total'] or 0

    gas_usage = Bill.objects.filter(
        customer=customer_profile,
        connection_type='GAS'
    ).aggregate(total=Sum('units_consumed'))['total'] or 0

    context = {
        'customer': customer_profile,
        'unpaid_bills': unpaid_bills,
        'total_due': total_due,
        'electricity_usage': electricity_usage,
        'water_usage': water_usage,
        'gas_usage': gas_usage,
    }

    return render(request, 'consumer/dashboard.html', context)


def admin_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
                if user.is_active:  # Check if user is active
                    auth_login(request, user)
                    messages.success(request, 'Login successful')

                    if user.is_superuser:
                        return redirect('admin_dashboard')
                    
                    elif user.role == 'STAFF':
                        return redirect('staff_dashboard')

                    else:
                        messages.error(request, 'Your account is inactive.')
                        return redirect('admin_login')
        else:
             messages.error(request, 'Invalid username or password.')

    return render(request, 'admin_panel/login.html')
    
@login_required(login_url='admin_login') 

def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


@login_required
def admin_dashboard(request):


    total_consumers = Customer.objects.count()

    total_connections = Bill.objects.values(
        'customer', 'connection_type'
    ).distinct().count()

    pending_bills = Bill.objects.filter(is_paid=False).count()

    total_revenue = Payment.objects.filter(
        status='SUCCESS'
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    # -----------------------------
    # CURRENT MONTH REVENUE
    # -----------------------------
    today = now()

    monthly_revenue = Payment.objects.filter(
        status='SUCCESS',
        created_at__year=today.year,
        created_at__month=today.month
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0

    # -----------------------------
    # RECENT BILLS
    # -----------------------------
    recent_bills = Bill.objects.select_related(
        'customer'
    ).order_by('-bill_date')[:10]

    utility_stats = Bill.objects.values(
        'connection_type'
    ).annotate(
        total=Count('id'),
        unpaid=Count('id', filter=Q(is_paid=False))
    )

    context = {
        'total_consumers': total_consumers,
        'total_connections': total_connections,
        'pending_bills': pending_bills,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'recent_bills': recent_bills,
        'utility_stats': utility_stats,
    }

    return render(request, 'admin_panel/dashboard.html', context)

def bills(request):
    customer = Customer.objects.get(user=request.user)

    bills = Bill.objects.filter(
        customer=customer
    ).order_by('-bill_date')

    context = {
        'bills': bills
    }

    return render(request, 'consumer/bill.html', context)

from .models import MeterReading, Tariff
@login_required
def usage_tracking(request):
    user = request.user

    if user.role != 'CUSTOMER':
        return redirect('home')

    customer = Customer.objects.get(user=user)

    bills = Bill.objects.filter(customer=customer).order_by('-bill_date')

    usage_data = []

    for bill in bills:
        tariff = Tariff.objects.filter(
            utility_type=bill.connection_type
        ).first()

        rate = tariff.rate_per_unit if tariff else 0

        usage_data.append({
            'utility': bill.connection_type,
            'month': bill.month,
            'units_consumed': bill.units_consumed,  # Changed from 'units' to match template
            'rate': rate,
            'amount': bill.total_amount,
            'due_date': bill.due_date,
            'status': 'Paid' if bill.is_paid else 'Unpaid',
            'created_at': bill.bill_date,  # Add this for the date display
            'connection_type': bill.connection_type  # Add this for the utility type
        })

    # Calculate current month and previous month data
    current_month = None
    previous_month = None
    comparison = None
    
    if usage_data:
        current_month = usage_data[0]  # Most recent bill
        
        if len(usage_data) > 1:
            previous_month = usage_data[1]  # Second most recent bill
            
            # Calculate difference
            if current_month and previous_month:
                comparison = current_month['units_consumed'] - previous_month['units_consumed']
    
    # Calculate estimated bill (you might want to adjust this logic)
    estimated_bill = 0
    if current_month and current_month.get('rate'):
        estimated_bill = current_month['units_consumed'] * current_month['rate']
    
    # Check for high usage alert (you can adjust the threshold)
    high_usage_alert = False
    limit = 500  # Example threshold
    if current_month and current_month['units_consumed'] > limit:
        high_usage_alert = True

    context = {
        'readings': usage_data,  # This matches the template's 'readings' variable
        'current_month': current_month,
        'previous_month': previous_month,
        'comparison': comparison,
        'estimated_bill': estimated_bill,
        'high_usage_alert': high_usage_alert,
        'limit': limit,
    }
    
    return render(request, 'consumer/utility.html', context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect ,get_object_or_404
from .models import Customer, MeterReading, Bill


@login_required
def profile(request):
    user = request.user  # Custom User model (has phone, role)

    # Get customer safely
    customer = get_object_or_404(Customer, user=user)

    # Utility connections (derived from bills)
    connections = (
        Bill.objects
        .filter(customer=customer)
        .values('connection_type')
        .distinct()
    )

    # Latest meter reading (any utility)
    meter = (
        MeterReading.objects
        .filter(customer=customer)
        .order_by('-month')
        .first()
    )

    context = {
        'user': user,               # {{ user.email }}, {{ user.phone }}
        'customer': customer,       # {{ customer.address }}, {{ customer.customer_id }}
        'connections': connections, # Used in utility badges
        'meter': meter,             # Meter table
    }

    return render(request, 'consumer/profile.html', context)

@login_required
def edit_profile(request):
    user = request.user
    customer = get_object_or_404(Customer, user=user)

    if request.method == 'POST':
        # User fields
        user.first_name = request.POST.get('name')
        user.email = request.POST.get('email')
        user.phone = request.POST.get('phone')
        user.save()

        # Customer fields
        customer.address = request.POST.get('address')
        customer.save()

        return redirect('profile')

    return render(request, 'consumer/edit_profile.html', {
        'customer': customer
    })
    
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash  
from django.http import JsonResponse
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)

        if form.is_valid():
            user = form.save()
            # IMPORTANT: keeps user logged in
            update_session_auth_hash(request, user)

            messages.success(request, 'Password updated successfully.')
            return redirect('profile')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'consumer/password.html', {
        'form': form
    })
    

@login_required

def add_connection(request):
    customer = Customer.objects.get(user=request.user)

    if request.method == 'POST':
        connection_type = request.POST.get('connection_type')

        if not connection_type:
            messages.error(request, "Please select a connection type.")
            return redirect('add_connection')

        # ❌ Prevent duplicate connection
        exists = Bill.objects.filter(
            customer=customer,
            connection_type=connection_type
        ).exists()

        if exists:
            messages.warning(
                request,
                f"{connection_type.title()} connection already exists."
            )
            return redirect('profile')

        # ✅ Create initial bill (0 units)
        Bill.objects.create(
            customer=customer,
            connection_type=connection_type,
            month="Initial",
            units_consumed=0,
            rate_per_unit=0,
            total_amount=0,
            due_date="2030-01-01"
        )

        messages.success(
            request,
            f"{connection_type.title()} connection added successfully."
        )
        return redirect('profile')

    return render(request, 'consumer/add_con.html')


@login_required

def notifications(request):
    customer = Customer.objects.get(user=request.user)

    # ----------------------------
    # MOCK NOTIFICATIONS (for now)
    # ----------------------------
    notifications = []

    bills = Bill.objects.filter(customer=customer).order_by('-bill_date')[:5]

    for bill in bills:
        notifications.append({
            "type": "bill",
            "unread": True,
            "icon": "fas fa-file-invoice-dollar",
            "title": "New Bill Generated",
            "message": f"Your {bill.connection_type.title()} bill for {bill.month} is ready.",
            "time": bill.bill_date.strftime("%d %b %Y"),
            "amount": bill.total_amount,
            "utility": bill.connection_type.title(),
            "utility_icon": "fas fa-bolt" if bill.connection_type == "ELECTRICITY"
                            else "fas fa-tint" if bill.connection_type == "WATER"
                            else "fas fa-fire",
            "due_date": bill.due_date.strftime("%d %b %Y"),
            "actions": [
                {
                    "label": "Pay Now",
                    "icon": "fas fa-credit-card",
                    "class": "primary",
                    "onclick": f"window.location.href='/consumer/bill/{bill.id}/'"
                }
            ]
        })

    # ----------------------------
    # COUNTS FOR DASHBOARD
    # ----------------------------
    unread_count = len(notifications)

    bill_alerts_count = len(notifications)
    due_reminders_count = Bill.objects.filter(
        customer=customer,
        is_paid=False
    ).count()

    penalty_alerts_count = Bill.objects.filter(
        customer=customer,
        is_paid=False,
        due_date__lt=now().date()
    ).count()

    context = {
        "notifications": notifications,
        "unread_count": unread_count,
        "bill_alerts_count": bill_alerts_count,
        "due_reminders_count": due_reminders_count,
        "penalty_alerts_count": penalty_alerts_count,
    }

    return render(request, "consumer/notification.html", context)


@login_required

def payment_history(request):
    customer = get_object_or_404(Customer, user=request.user)

    # Payment History
    payments = Payment.objects.filter(
        customer=customer
    ).select_related('bill').order_by('-created_at')

    # Billing History
    bills = Bill.objects.filter(
        customer=customer
    ).order_by('-bill_date')

    context = {
        'payments': payments,
        'bills': bills,
    }

    return render(request, 'consumer/payment_his.html', context)



def admin_user_management(request):

    consumers = Customer.objects.select_related('user').all()
    staffs = Staff.objects.select_related('user').all()

    context = {
        'consumers': consumers,
        'staffs': staffs,   # 🔥 THIS MUST BE HERE
        'total_consumers': consumers.count(),
        'active_consumers': consumers.filter(user__is_active=True).count(),
        'total_staff': staffs.count(),
        'total_staff_count': staffs.count(),
        'pending_count': staffs.filter(is_approved=False).count(),
        'approved_count': staffs.filter(is_approved=True).count(),
        'pending_staff_approvals': staffs.filter(is_approved=False).count(),
    }

    return render(request, 'admin_panel/consumer.html', context)




@login_required


def admin_toggle_consumer_status(request, customer_id):
    customer = get_object_or_404(Customer, customer_id=customer_id)
    user = customer.user
    
    # Toggle the status
    user.is_active = not user.is_active
    user.save()
    
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f'Consumer {"activated" if user.is_active else "deactivated"} successfully.'
        })
    else:
        # Regular form/GET request
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f'Consumer {user.get_full_name()} has been {status} successfully.')
        return redirect('admin_consumer_list')
    
def admin_consumer_list(request):
    customers = Customer.objects.all()
    return render(request, '', {
        'customers': customers
    })

def ad_edit_consumer(request, customer_id):
    customer = get_object_or_404(Customer, customer_id=customer_id)
    user = customer.user

    if request.method == 'POST':
        # USER FIELDS
        user.first_name = request.POST.get('first_name')
        user.email = request.POST.get('email')
        user.phone = request.POST.get('phone')
        user.save()

        # CUSTOMER FIELDS
        customer.address = request.POST.get('address')
        customer.connection_type = request.POST.get('connection_type')
        customer.save()

        return redirect('admin_user_management')

    context = {
        'customer': customer,
        'user_obj': user
    }
    return render(request, 'admin_panel/edit_consumer.html', context)

@login_required

def ad_view_consumer(request, customer_id):
    """
    Admin – View single consumer details (READ ONLY)
    """

    # Fetch customer safely
    customer = get_object_or_404(Customer, customer_id=customer_id)

    context = {
        'customer': customer,
        'user_obj': customer.user,   # linked User model
    }

    return render(request, 'admin_panel/view.html', context)

def approve_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    staff.is_approved = True
    staff.save()

    return JsonResponse({
        "success": True,
        "message": "Staff approved successfully"
    })

@login_required
def reject_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    staff.user.delete()

    return JsonResponse({
        "success": True,
        "message": "Staff rejected and account deleted"
    })

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import Staff

@login_required
def staff_details(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)

    context = {
        'staff': staff
    }

    # If AJAX request → return partial HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'admin_panel/staff_details_partial.html', context)

    # Normal page load
    return render(request, 'admin_panel/staff_view.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Bill, Staff, Tariff

@login_required


def update_bill(request, bill_id):

    bill = get_object_or_404(Bill, id=bill_id)

    # SECURITY CHECK
    if not request.user.is_superuser and request.user.role == 'STAFF':

        staff_profile = request.user.staff_profile

        if bill.connection_type != staff_profile.utility_type:
            return JsonResponse({'error': 'Access denied'}, status=403)

    new_units = Decimal(request.POST.get('units'))

    bill.units_consumed = new_units
    bill.total_amount = new_units * bill.rate_per_unit
    bill.save()

    return JsonResponse({
        'success': True,
        'new_total': float(bill.total_amount)
    })
def toggle_status(request, bill_id):
    bill = get_object_or_404(Bill, id=bill_id)

    if not request.user.is_superuser and request.user.role == 'STAFF':
        staff_profile = request.user.staff_profile
        if bill.connection_type != staff_profile.utility_type:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Access denied'}, status=403)
            else:
                messages.error(request, 'Access denied')
                return redirect('admin_panel:admin_bill_list')

    bill.is_paid = not bill.is_paid
    bill.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'status': bill.is_paid
        })
    else:
        messages.success(request, f'Bill status updated to {"Paid" if bill.is_paid else "Unpaid"}')
        return redirect('admin_panel:admin_bill_list')
    
    # views/staff_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
import calendar
from decimal import Decimal

from .models import User, Customer, Staff, Bill, Payment, MeterReading, Tariff

# Helper function to check if user is approved staff
def is_approved_staff(user):
    """Check if user is an approved staff member"""
    if not user.is_authenticated:
        return False
    try:
        staff = Staff.objects.get(user=user)
        return staff.is_approved and staff.is_active
    except Staff.DoesNotExist:
        return False

# Staff Dashboard View
@login_required
def staff_dashboard(request):
    """Main staff dashboard view"""
    user = request.user
    
    # Check if user is staff
    try:
        staff_profile = Staff.objects.get(user=user)
    except Staff.DoesNotExist:
        messages.error(request, "You are not authorized as staff.")
        return redirect('login')
    
    # If not approved, show pending approval page
    if not staff_profile.is_approved:
        context = {
            'staff_profile': staff_profile,
            'user': user
        }
        return render(request, 'staff/dashboard.html', context)
    
    today = timezone.now().date()
    
    # Get consumers for this staff's utility type
    consumers = Customer.objects.filter(
        connection_type=staff_profile.utility_type
    ).select_related('user').order_by('-id')
    
    # Get bills for this staff's utility type
    bills = Bill.objects.filter(
        connection_type=staff_profile.utility_type
    ).select_related('customer', 'customer__user').order_by('-created_at')
    
    # Get recent bills (last 5)
    recent_bills = bills.filter(
        Q(is_paid=False) | Q(due_date__lt=today)
    )[:5]
    
    # Get payments for this utility
    payments = Payment.objects.filter(
        customer__connection_type=staff_profile.utility_type
    ).select_related('customer', 'customer__user', 'bill').order_by('-created_at')[:10]
    
    # Calculate statistics
    consumers_count = consumers.count()
    
    # Bill statistics
    pending_bills_count = bills.filter(is_paid=False, due_date__gte=today).count()
    overdue_bills_count = bills.filter(is_paid=False, due_date__lt=today).count()
    paid_bills_count = bills.filter(is_paid=True).count()
    total_bills_count = bills.count()
    
    # Current month collection
    current_month = today.month
    current_year = today.year
    monthly_collection = Payment.objects.filter(
        customer__connection_type=staff_profile.utility_type,
        status='SUCCESS',
        created_at__month=current_month,
        created_at__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Previous month collection for comparison
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    prev_month_collection = Payment.objects.filter(
        customer__connection_type=staff_profile.utility_type,
        status='SUCCESS',
        created_at__month=prev_month,
        created_at__year=prev_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate collection change percentage
    if prev_month_collection > 0:
        collection_change = ((monthly_collection - prev_month_collection) / prev_month_collection) * 100
    else:
        collection_change = 100 if monthly_collection > 0 else 0
    
    # Total consumption this month
    total_consumption = bills.filter(
        bill_date__month=current_month,
        bill_date__year=current_year
    ).aggregate(Sum('units_consumed'))['units_consumed__sum'] or 0
    
    # Average consumption
    if bills.count() > 0:
        avg_consumption = bills.aggregate(Sum('units_consumed'))['units_consumed__sum'] / bills.count()
    else:
        avg_consumption = 0
    
    # Overdue amount
    overdue_amount = bills.filter(
        is_paid=False,
        due_date__lt=today
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Collection percentage
    if total_bills_count > 0:
        collection_percentage = (paid_bills_count / total_bills_count) * 100
    else:
        collection_percentage = 0
    
    # Default rate from tariff
    default_rate = Tariff.objects.filter(
        utility_type=staff_profile.utility_type,
        is_active=True
    ).first()
    default_rate_value = default_rate.rate_per_unit if default_rate else Decimal('8.50')
    
    # Default due date (30 days from now)
    default_due_date = today + timedelta(days=30)
    
    # Current month for billing
    current_month_str = today.strftime('%Y-%m')
    
    # Consumption trend data for last 6 months
    consumption_labels = []
    consumption_data = []
    
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_name = month_date.strftime('%b')
        consumption_labels.append(month_name)
        
        month_consumption = bills.filter(
            bill_date__month=month_date.month,
            bill_date__year=month_date.year
        ).aggregate(Sum('units_consumed'))['units_consumed__sum'] or 0
        
        consumption_data.append(float(month_consumption))
    
    # Pagination for consumers
    consumers_paginator = Paginator(consumers, 10)
    consumers_page = request.GET.get('page', 1)
    consumers = consumers_paginator.get_page(consumers_page)
    
    # Pagination for bills
    bills_paginator = Paginator(bills, 10)
    bills_page = request.GET.get('page', 1)
    bills = bills_paginator.get_page(bills_page)
    
    context = {
        'staff_profile': staff_profile,
        'user': user,
        'consumers': consumers,
        'bills': bills,
        'recent_bills': recent_bills,
        'payments': payments,
        'today': today,
        'consumers_count': consumers_count,
        'pending_bills_count': pending_bills_count,
        'overdue_bills_count': overdue_bills_count,
        'paid_bills_count': paid_bills_count,
        'total_bills_count': total_bills_count,
        'monthly_collection': monthly_collection,
        'collection_change': collection_change,
        'total_consumption': total_consumption,
        'avg_consumption': avg_consumption,
        'overdue_amount': overdue_amount,
        'collection_percentage': collection_percentage,
        'default_rate': default_rate_value,
        'default_due_date': default_due_date,
        'current_month': current_month_str,
        'consumption_labels': consumption_labels,
        'consumption_data': consumption_data,
    }
    
    return render(request, 'staff/dashboard.html', context)

def toggle_staff_active(request, staff_id):
    try:
        # Assuming you have a Staff model
        staff = get_object_or_404(Staff, id=staff_id)
        
        # Toggle the active status
        staff.is_active = not staff.is_active
        staff.save()
        
        status = "activated" if staff.is_active else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Staff member has been {status} successfully',
            'is_active': staff.is_active
        })
    except Staff.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Staff member not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
   

# Generate Bill Manually
@login_required
def generate_bill_manual(request):
    """Generate a new bill manually"""
    if request.method != 'POST':
        return redirect('staff_dashboard')
    
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            messages.error(request, "Your account is not approved yet.")
            return redirect('staff_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('login')
    
    # Get form data
    customer_id = request.POST.get('customer')
    month = request.POST.get('month')
    units_consumed = request.POST.get('units_consumed')
    rate_per_unit = request.POST.get('rate_per_unit')
    due_date = request.POST.get('due_date')
    
    # Validate
    if not all([customer_id, month, units_consumed, rate_per_unit, due_date]):
        messages.error(request, "All fields are required.")
        return redirect('staff_dashboard')
    
    try:
        customer = Customer.objects.get(id=customer_id)
        
        # Verify customer belongs to staff's utility
        if customer.connection_type != staff_profile.utility_type:
            messages.error(request, "You can only generate bills for your assigned utility type.")
            return redirect('staff_dashboard')
        
        # Calculate total amount
        units = Decimal(units_consumed)
        rate = Decimal(rate_per_unit)
        total_amount = units * rate
        
        # Create bill
        bill = Bill.objects.create(
            customer=customer,
            connection_type=customer.connection_type,
            month=month,
            units_consumed=units,
            rate_per_unit=rate,
            total_amount=total_amount,
            due_date=due_date,
            generated_by=staff_profile,
            is_paid=False
        )
        
        messages.success(request, f"Bill #{bill.id} generated successfully for {customer.user.get_full_name()}.")
        
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
    except Exception as e:
        messages.error(request, f"Error generating bill: {str(e)}")
    
    return redirect('staff_dashboard')

# Record Meter Reading
@login_required
def record_reading(request):
    """Record a new meter reading"""
    if request.method != 'POST':
        return redirect('staff_dashboard')
    
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            messages.error(request, "Your account is not approved yet.")
            return redirect('staff_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('login')
    
    # Get form data
    customer_id = request.POST.get('customer')
    reading_date = request.POST.get('reading_date')
    units_consumed = request.POST.get('units_consumed')
    notes = request.POST.get('notes', '')
    
    # Validate
    if not all([customer_id, reading_date, units_consumed]):
        messages.error(request, "Customer, reading date, and units are required.")
        return redirect('staff_dashboard')
    
    try:
        customer = Customer.objects.get(id=customer_id)
        
        # Verify customer belongs to staff's utility
        if customer.connection_type != staff_profile.utility_type:
            messages.error(request, "You can only record readings for your assigned utility type.")
            return redirect('staff_dashboard')
        
        # Parse reading date to first day of month
        reading_datetime = datetime.strptime(reading_date, '%Y-%m-%d')
        month_first = reading_datetime.replace(day=1).date()
        
        # Check if reading already exists for this month
        existing_reading = MeterReading.objects.filter(
            customer=customer,
            utility_type=customer.connection_type,
            month=month_first
        ).first()
        
        if existing_reading:
            messages.warning(request, f"A reading for {month_first.strftime('%B %Y')} already exists. Updating it.")
            existing_reading.units_consumed = Decimal(units_consumed)
            existing_reading.recorded_by = staff_profile
            existing_reading.save()
        else:
            # Create new reading
            MeterReading.objects.create(
                customer=customer,
                utility_type=customer.connection_type,
                month=month_first,
                units_consumed=Decimal(units_consumed),
                recorded_by=staff_profile
            )
        
        messages.success(request, f"Meter reading recorded for {customer.user.get_full_name()}.")
        
    except Customer.DoesNotExist:
        messages.error(request, "Customer not found.")
    except ValueError:
        messages.error(request, "Invalid date format.")
    except Exception as e:
        messages.error(request, f"Error recording reading: {str(e)}")
    
    return redirect('staff_dashboard')

# Mark Bill as Paid
@require_POST
@login_required

def mark_bill_paid(request, bill_id):
    """Mark a bill as paid (AJAX endpoint)"""
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            return JsonResponse({'success': False, 'error': 'Not approved'})
    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    try:
        bill = Bill.objects.get(id=bill_id)
        
        # Verify bill belongs to staff's utility
        if bill.connection_type != staff_profile.utility_type:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
        bill.is_paid = True
        bill.save()
        
        # Create payment record
        Payment.objects.create(
            customer=bill.customer,
            bill=bill,
            amount=bill.total_amount,
            status='SUCCESS',
            transaction_id=f"MANUAL-{bill.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        return JsonResponse({'success': True})
        
    except Bill.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Bill not found'})

# Get Bill Details (AJAX)
@login_required
def get_bill_details(request, bill_id):
    """Get bill details for modal (AJAX endpoint)"""
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            return JsonResponse({'success': False, 'error': 'Not approved'})
    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    try:
        bill = Bill.objects.select_related('customer', 'customer__user').get(id=bill_id)
        
        # Verify bill belongs to staff's utility
        if bill.connection_type != staff_profile.utility_type:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
        unit = 'kWh'
        if bill.connection_type == 'WATER':
            unit = 'KL'
        elif bill.connection_type == 'GAS':
            unit = 'm³'
        
        return JsonResponse({
            'success': True,
            'bill': {
                'id': bill.id,
                'consumer_name': bill.customer.user.get_full_name() or bill.customer.user.username,
                'consumer_id': bill.customer.customer_id,
                'month': bill.month,
                'units_consumed': float(bill.units_consumed),
                'rate_per_unit': float(bill.rate_per_unit),
                'total_amount': float(bill.total_amount),
                'bill_date': bill.bill_date.isoformat(),
                'due_date': bill.due_date.isoformat(),
                'is_paid': bill.is_paid,
                'unit': unit
            }
        })
        
    except Bill.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Bill not found'})

# Get Last Reading (AJAX)
@login_required
def get_last_reading(request, customer_id):
    """Get last meter reading for a customer (AJAX endpoint)"""
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            return JsonResponse({'success': False, 'error': 'Not approved'})
    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    try:
        customer = Customer.objects.get(id=customer_id)
        
        # Verify customer belongs to staff's utility
        if customer.connection_type != staff_profile.utility_type:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
        last_reading = MeterReading.objects.filter(
            customer=customer
        ).order_by('-month').first()
        
        if last_reading:
            unit = 'kWh'
            if last_reading.utility_type == 'WATER':
                unit = 'KL'
            elif last_reading.utility_type == 'GAS':
                unit = 'm³'
                
            return JsonResponse({
                'success': True,
                'reading': {
                    'units_consumed': float(last_reading.units_consumed),
                    'month': last_reading.month.strftime('%B %Y'),
                    'unit': unit
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'No previous reading found'})
            
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Customer not found'})

# Get Consumer Details (AJAX)
@login_required
def get_consumer_details(request, consumer_id):
    """Get consumer details (AJAX endpoint)"""
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            return JsonResponse({'success': False, 'error': 'Not approved'})
    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not authorized'})
    
    try:
        consumer = Customer.objects.select_related('user').get(id=consumer_id)
        
        # Verify consumer belongs to staff's utility
        if consumer.connection_type != staff_profile.utility_type:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
        return JsonResponse({
            'success': True,
            'consumer': {
                'name': consumer.user.get_full_name() or consumer.user.username,
                'customer_id': consumer.customer_id,
                'phone': consumer.user.phone or 'N/A',
                'address': consumer.address,
                'connection_type': consumer.get_connection_type_display()
            }
        })
        
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Consumer not found'})

# Download Bill PDF
@login_required
def download_bill_pdf(request, bill_id):
    """Download bill as PDF"""
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            messages.error(request, "Your account is not approved yet.")
            return redirect('staff_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('login')
    
    try:
        bill = Bill.objects.select_related('customer', 'customer__user', 'generated_by').get(id=bill_id)
        
        # Verify bill belongs to staff's utility
        if bill.connection_type != staff_profile.utility_type:
            messages.error(request, "You don't have permission to download this bill.")
            return redirect('staff_dashboard')
        
        # Import PDF generation library
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas
        from django.http import HttpResponse
        import io
        
        # Create PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add content
        p.setFont("Helvetica-Bold", 16)
        p.drawString(1*inch, height-1*inch, f"{bill.get_connection_type_display()} BILL")
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1*inch, height-1.5*inch, f"Bill ID: {bill.id}")
        
        p.setFont("Helvetica", 11)
        y = height - 2*inch
        
        # Customer Info
        p.drawString(1*inch, y, f"Customer ID: {bill.customer.customer_id}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Name: {bill.customer.user.get_full_name() or bill.customer.user.username}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Address: {bill.customer.address}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Connection Type: {bill.get_connection_type_display()}")
        
        y -= 0.5*inch
        # Bill Details
        p.drawString(1*inch, y, f"Month: {bill.month}")
        y -= 0.3*inch
        
        unit = 'kWh'
        if bill.connection_type == 'WATER':
            unit = 'KL'
        elif bill.connection_type == 'GAS':
            unit = 'm³'
            
        p.drawString(1*inch, y, f"Units Consumed: {bill.units_consumed} {unit}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Rate per Unit: ₹{bill.rate_per_unit}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Subtotal: ₹{bill.units_consumed * bill.rate_per_unit}")
        y -= 0.3*inch
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1*inch, y, f"Total Amount: ₹{bill.total_amount}")
        y -= 0.3*inch
        
        p.setFont("Helvetica", 11)
        p.drawString(1*inch, y, f"Bill Date: {bill.bill_date.strftime('%d %B %Y')}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Due Date: {bill.due_date.strftime('%d %B %Y')}")
        y -= 0.3*inch
        
        # Status
        status = "PAID" if bill.is_paid else "OVERDUE" if bill.due_date < timezone.now().date() else "UNPAID"
        p.drawString(1*inch, y, f"Status: {status}")
        
        # Generated by
        if bill.generated_by:
            y -= 0.5*inch
            p.setFont("Helvetica-Oblique", 10)
            p.drawString(1*inch, y, f"Generated by: {bill.generated_by.user.get_full_name() or bill.generated_by.user.username}")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        
        # Create response
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="bill_{bill.customer.customer_id}_{bill.month}.pdf"'
        
        return response
        
    except Bill.DoesNotExist:
        messages.error(request, "Bill not found.")
        return redirect('staff_dashboard')

# Edit Bill (if needed)
@login_required
def edit_bill(request, bill_id):
    """Edit bill page"""
    try:
        staff_profile = Staff.objects.get(user=request.user)
        if not staff_profile.is_approved:
            messages.error(request, "Your account is not approved yet.")
            return redirect('staff_dashboard')
    except Staff.DoesNotExist:
        messages.error(request, "Staff profile not found.")
        return redirect('login')
    
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Verify bill belongs to staff's utility
    if bill.connection_type != staff_profile.utility_type:
        messages.error(request, "You don't have permission to edit this bill.")
        return redirect('staff_dashboard')
    
    if request.method == 'POST':
        try:
            # Update bill fields
            units = request.POST.get('units_consumed')
            rate = request.POST.get('rate_per_unit')
            due_date = request.POST.get('due_date')
            is_paid = request.POST.get('is_paid') == 'on'
            
            if units:
                bill.units_consumed = Decimal(units)
            if rate:
                bill.rate_per_unit = Decimal(rate)
            if due_date:
                bill.due_date = due_date
            
            bill.is_paid = is_paid
            
            # Recalculate total
            bill.total_amount = bill.units_consumed * bill.rate_per_unit
            bill.save()
            
            messages.success(request, f"Bill #{bill.id} updated successfully.")
            return redirect('staff_dashboard')
            
        except Exception as e:
            messages.error(request, f"Error updating bill: {str(e)}")
    
    context = {
        'bill': bill,
        'staff_profile': staff_profile,
        'today': timezone.now().date()
    }
    return render(request, 'staff/edit_bill.html', context)

def logout(request):
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

@login_required
def admin_bill_detail(request, bill_id):
    # Optional: restrict only ADMIN role

    bill = get_object_or_404(
        Bill.objects.select_related(
            'customer__user',
            'generated_by__user'
        ).prefetch_related('payments'),
        id=bill_id
    )

    context = {
        "bill": bill,
        "today": now().date(),
    }

    return render(request, "admin_panel/bill.html", context)

@login_required
def admin_bill_list(request):

    bills = Bill.objects.select_related(
        "customer__user",
        "generated_by__user"
    ).all().order_by("-id")

    return render(request, "admin_panel/bill_list.html", {
        "bills": bills
    })

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def tariff_billing_config(request):

    if request.method == "POST":
        # Tariff Setup
        slab_1_rate = request.POST.get("slab_1_rate")
        slab_2_rate = request.POST.get("slab_2_rate")
        fixed_charge = request.POST.get("fixed_charge")
        tax_percentage = request.POST.get("tax_percentage")
        late_penalty = request.POST.get("late_penalty")

        # Billing Rules
        billing_cycle = request.POST.get("billing_cycle")
        due_days = request.POST.get("due_days")
        auto_generate = request.POST.get("auto_generate")
        penalty_after_days = request.POST.get("penalty_after_days")

        # Save logic here (if using model)
        # Example:
        # TariffConfig.objects.update_or_create(...)

        messages.success(request, "Tariff & Billing Configuration Updated Successfully!")

        return redirect("tariff_billing_config")

    return render(request, "admin_panel/tariff.html")

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def notifications_management(request):


    if request.method == "POST":
        bill_reminder_days = request.POST.get("bill_reminder_days")
        payment_due_alert = request.POST.get("payment_due_alert")
        overdue_notification = request.POST.get("overdue_notification")
        system_announcement = request.POST.get("system_announcement")
        maintenance_alert = request.POST.get("maintenance_alert")

        # You can save this to DB model here if needed

        messages.success(request, "Notification Settings Updated Successfully!")
        return redirect("notifications_management")

    return render(request, "admin_panel/notification.html")

import razorpay

def create_order(request, bill_id):
    bill = Bill.objects.get(id=bill_id)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    order = client.order.create({
        "amount": int(float(bill.total_amount) * 100),  # 🔥 important
        "currency": "INR",
        "payment_capture": 1
    })

    # 🔥 MUST SAVE ORDER ID
    bill.razorpay_order_id = order["id"]
    bill.save()

    return JsonResponse({
        "order_id": order["id"],
        "amount": int(float(bill.total_amount) * 100),
        "key": settings.RAZORPAY_KEY_ID
    })
    
import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)

        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")

        client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        try:
            # 🔐 VERIFY SIGNATURE
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })

            bill = Bill.objects.get(razorpay_order_id=razorpay_order_id)

            # ✅ SAVE PAYMENT
            payment = Payment.objects.create(
                customer=bill.customer,
                bill=bill,
                amount=bill.total_amount,
                status="SUCCESS",
                transaction_id=razorpay_payment_id
            )

            bill.is_paid = True
            bill.save()

            return JsonResponse({"message": "Payment Successful"})

        except Exception as e:
            print("ERROR:", str(e))  # 🔥 See real error in terminal

            return JsonResponse({
                "message": "Payment Failed",
                "error": str(e)
            })