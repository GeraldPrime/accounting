# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Branch Management
    path('create-branch/', views.create_branch, name='create_branch'),
    path('manage-branches/', views.manage_branches, name='manage_branches'),
    path('assign-branch-admin/', views.assign_branch_admin, name='assign_branch_admin'),
    path('delete-branch/<int:branch_id>/', views.delete_branch, name='delete_branch'),

    # User Management
    path('create-branch-admin/', views.create_branch_admin, name='create_branch_admin'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('toggle-user-status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('reset-password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),

    # Fund Management
    path('allocate-funds/', views.allocate_funds, name='allocate_funds'),
    path('fund-allocations/', views.fund_allocations, name='fund_allocations'),

    # Transactions
    path('transactions/', views.transactions, name='transactions'),
    path('add-transaction/', views.add_transaction, name='add_transaction'),
    path('add-income/', views.add_income, name='add_income'),
    path('add-expenditure/', views.add_expenditure, name='add_expenditure'),
    path('delete-transaction/<int:transaction_id>/', views.delete_transaction, name='delete_transaction'),

    # Categories
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    path('add-income-category/', views.add_income_category, name='add_income_category'),
    path('add-expenditure-category/', views.add_expenditure_category, name='add_expenditure_category'),
    
    # Reports
    path('reports/', views.reports, name='reports'),
]
