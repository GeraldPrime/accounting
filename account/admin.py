# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'phone')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Branch)
admin.site.register(IncomeCategory)
admin.site.register(ExpenditureCategory)
admin.site.register(Transaction)