"""
URL configuration for bill_mp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from app import views

urlpatterns = [
    # path('/', admin.site.urls),
    path('', views.home, name='home'),
    path('features/', views.features_view, name='features_view'),
    path('about/', views.about_view, name='about_view'),
    path('consumer/register/', views.register, name='register'),
    path('consumer/login/', views.customer_login, name='customer_login'),
    path("consumer/forgot-password/", views.forgot_password, name="forgot_password"),
    path("consumer/verify-otp/", views.verify_otp, name="verify_otp"),
    path("consumer/reset-password/", views.reset_password, name="reset_password"),
    path("consumer/customer_dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path('consumer/bills/', views.bills, name='bills'),
    path('consumer/usage_tracking/',views.usage_tracking,name="usage_tracking"),
    path('consumer/profile/',views.profile,name='profile'),
    path('consumer/profile/edit/',views.edit_profile,name='edit_profile'),
    path('consumer/password/',views.password_change,name='password_change'),
    path('consumer/add_connection',views.add_connection,name='add_connection'),
    path('consumer/notifications/',views.notifications,name='notifications'),
    path('consumer/payment_history/',views.payment_history,name='payment_history'),
    

    # Admin
    path('admin_panel/login/', views.admin_login, name='admin_login'),
    path('admin_panel/admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_panel/consumers/',views.admin_user_management,name='admin_user_management'),
    path('admin_panel/consumers/toggle/<str:customer_id>/',views.admin_toggle_consumer_status,name='admin_toggle_consumer_status'),
    path('admin_panel/consumers/edit/<str:customer_id>/',views.ad_edit_consumer,name='ad_edit_consumer'),
    path('admin_panel/consumers/view/<str:customer_id>/',views.ad_view_consumer,name='ad_view_consumer'),
    path('admin/staff/<int:staff_id>/approve/', views.approve_staff, name='approve_staff'),
    path('admin/staff/<int:staff_id>/reject/', views.reject_staff, name='reject_staff'),
    path('admin/staff/<int:staff_id>/details/', views.staff_details, name='staff_details'),
    path('admin_panel/consumers/',views.admin_consumer_list,name='admin_consumer_list'),
    # path("admin_panel/bill/<int:bill_id>/",views.admin_bill_detail,name="admin_bill_detail"),
    
    path("admin_panel/bills/", views.admin_bill_list, name="admin_bill_list"),
    path("admin_panel/bill/<int:bill_id>/", views.admin_bill_detail, name="admin_bill_detail"),
    path("admin_panel/tariff-config/",views.tariff_billing_config,name="tariff_billing_config"),
    path("admin_panel/notifications/",views.notifications_management,name="notifications_management"),
    path('admin/staff/<int:staff_id>/toggle-active/', views.toggle_staff_active, name='toggle_staff_active'),


    
    # STAFF
     
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/update/<int:bill_id>/', views.update_bill, name='update_bill'),
    path('staff/toggle/<int:bill_id>/', views.toggle_status, name='toggle_status'),
    path('bill/generate/', views.generate_bill_manual, name='generate_bill_manual'),
    path('bill/<int:bill_id>/edit/', views.edit_bill, name='edit_bill'),
    path('bill/<int:bill_id>/download/', views.download_bill_pdf, name='download_bill_pdf'),
    
    # Meter reading
    path('reading/record/', views.record_reading, name='record_reading'),
    
    # AJAX endpoints
    path('api/bill/<int:bill_id>/', views.get_bill_details, name='get_bill_details'),
    path('api/bill/<int:bill_id>/paid/', views.mark_bill_paid, name='mark_bill_paid'),
    path('api/last-reading/<int:customer_id>/', views.get_last_reading, name='get_last_reading'),
    path('api/consumer/<int:consumer_id>/', views.get_consumer_details, name='get_consumer_details'),
    path('logout/', views.logout, name='logout'),


    # payment
    
    path('create-order/<int:bill_id>/', views.create_order),
    path('verify-payment/', views.verify_payment),

]

    



