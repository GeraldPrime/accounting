# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('username',)
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'phone')}),
    )

admin.site.register(User, CustomUserAdmin)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'location', 'state', 'branch_type', 'allocated_funds', 'is_active', 'created_date', 'created_by',
    )
    list_filter = ('state', 'branch_type', 'is_active', 'admins')
    search_fields = ('name', 'location', 'state', 'address', 'admins__username', 'admins__email')
    readonly_fields = ('created_date',)
    autocomplete_fields = ('created_by',)
    filter_horizontal = ('admins',)
    ordering = ('-created_date',)


@admin.register(IncomeCategory)
class IncomeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'branch', 'is_active', 'created_by')
    list_filter = ('scope', 'is_active', 'branch')
    search_fields = ('name', 'description')
    autocomplete_fields = ('branch', 'created_by')
    ordering = ('name',)


@admin.register(ExpenditureCategory)
class ExpenditureCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'branch', 'is_active', 'created_by')
    list_filter = ('scope', 'is_active', 'branch')
    search_fields = ('name', 'description')
    autocomplete_fields = ('branch', 'created_by')
    ordering = ('name',)


@admin.register(FundAllocation)
class FundAllocationAdmin(admin.ModelAdmin):
    list_display = ('from_branch', 'to_branch', 'amount', 'allocated_by', 'allocated_date', 'is_active')
    list_filter = ('is_active', 'from_branch', 'to_branch', 'allocated_date')
    search_fields = ('description',)
    autocomplete_fields = ('from_branch', 'to_branch', 'allocated_by')
    date_hierarchy = 'allocated_date'
    ordering = ('-allocated_date',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('branch', 'transaction_type', 'amount', 'date', 'created_by', 'created_date')
    list_filter = ('transaction_type', 'branch', 'date')
    search_fields = ('description',)
    autocomplete_fields = ('branch', 'income_category', 'expenditure_category', 'fund_allocation', 'created_by')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_date')