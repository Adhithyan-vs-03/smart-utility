from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('CUSTOMER', 'Customer'),
        ('STAFF', 'Staff'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CUSTOMER'
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True
    )

    def __str__(self):
        return self.username
    
class Customer(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    customer_id = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    connection_type = models.CharField(
        max_length=20,
        choices=[
            ('ELECTRICITY', 'Electricity'),
            ('WATER', 'Water'),
            ('GAS', 'Gas')
        ]
    )

    def __str__(self):
        return self.customer_id
    
class Staff(models.Model):
        user = models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            related_name='staff_profile'
        )

        UTILITY_CHOICES = (
            ('ELECTRICITY', 'Electricity'),
            ('WATER', 'Water'),
            ('GAS', 'Gas'),
        )

        utility_type = models.CharField(max_length=20,choices=UTILITY_CHOICES )
        is_approved = models.BooleanField(default=False)
        is_active = models.BooleanField(default=True)
        
            
        approved_by = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name='approved_staff'
        )

        created_at = models.DateTimeField(auto_now_add=True)



def __str__(self):
    return f"{self.user.first_name} - {self.utility_type}"

class Bill(models.Model):

    CONNECTION_CHOICES = (
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='bills'
    )

    connection_type = models.CharField(
        max_length=20,
        choices=CONNECTION_CHOICES
    )

    month = models.CharField(max_length=20)

    units_consumed = models.DecimalField(max_digits=10, decimal_places=2)
    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    is_paid = models.BooleanField(default=False)

    bill_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()
    razorpay_order_id = models.CharField(max_length=200, null=True, blank=True)
    generated_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_bills'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_total(self):
        self.total_amount = self.units_consumed * self.rate_per_unit
        return self.total_amount

    def __str__(self):
        return f"{self.customer.customer_id} - {self.month}"



class Payment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.customer_id} - {self.amount}"

class MeterReading(models.Model):

    UTILITY_CHOICES = (
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='meter_readings'
    )

    utility_type = models.CharField(
        max_length=20,
        choices=UTILITY_CHOICES
    )

    month = models.DateField(help_text="Use first day of month (YYYY-MM-01)")

    units_consumed = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    recorded_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_readings'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'utility_type', 'month')
        ordering = ['-month']

    def __str__(self):
        return f"{self.customer.customer_id} | {self.utility_type} | {self.month}"

# app/models.py
class Tariff(models.Model):

    UTILITY_CHOICES = (
        ('ELECTRICITY', 'Electricity'),
        ('WATER', 'Water'),
        ('GAS', 'Gas'),
    )

    utility_type = models.CharField(
        max_length=20,
        choices=UTILITY_CHOICES
    )

    min_units = models.IntegerField()
    max_units = models.IntegerField()

    rate_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    fixed_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)


    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['utility_type', 'min_units']
        unique_together = ('utility_type', 'min_units', 'max_units')

    def __str__(self):
        return f"{self.utility_type} ({self.min_units}-{self.max_units})"





