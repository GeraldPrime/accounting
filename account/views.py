from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from decimal import Decimal
from .models import *
from .forms import *


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', False)

            user = authenticate(request, username=username, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Your account has been deactivated. Please contact the administrator.')
                    return render(request, 'signin.html', {'form': form})

                login(request, user)

                # Handle remember me functionality
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                    
                    

                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')

                # Redirect to next page if specified
                next_page = request.GET.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            # Convert form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = LoginForm()

    return render(request, 'signin.html', {'form': form})


@never_cache
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.user_type == 'super_admin':
        # Get main branch (Enugu) or create one if it doesn't exist
        main_branch, created = Branch.objects.get_or_create(
            branch_type='main',
            defaults={
                'name': 'Main Branch',
                'location': 'Enugu',
                'state': 'Enugu State',
                'address': 'Main Office Address',
                'created_by': request.user
            }
        )

        sub_branches = Branch.objects.filter(branch_type='sub', is_active=True).order_by('-created_date')
        all_branches = Branch.objects.filter(is_active=True)

        # Calculate totals
        main_income = main_branch.get_total_income()
        main_expenditure = main_branch.get_total_expenditure()
        main_balance = main_branch.get_balance()
        
        # Calculate available funds for allocation (main branch balance)
        available_for_allocation = main_balance

        # All branches combined
        total_income = Transaction.objects.filter(
            transaction_type='income',
            branch__is_active=True
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

        total_expenditure = Transaction.objects.filter(
            transaction_type='expenditure',
            branch__is_active=True
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

        total_balance = total_income - total_expenditure

        # Total allocated funds
        total_allocated = Branch.objects.filter(
            is_active=True
        ).aggregate(Sum('allocated_funds'))['allocated_funds__sum'] or Decimal('0')

        recent_transactions = Transaction.objects.filter(
            branch__is_active=True
        ).select_related('branch', 'created_by').order_by('-created_date')[:10]

        # Branch statistics
        active_admins = User.objects.filter(
            user_type='branch_admin',
            is_active=True
        ).count()

        context = {
            'main_branch': main_branch,
            'sub_branches': sub_branches,
            'all_branches': all_branches,
            'main_income': main_income,
            'main_expenditure': main_expenditure,
            'main_balance': main_balance,
            'available_for_allocation': available_for_allocation,
            'total_income': total_income,
            'total_expenditure': total_expenditure,
            'total_balance': total_balance,
            'total_allocated': total_allocated,
            'recent_transactions': recent_transactions,
            'branches_count': sub_branches.count(),
            'active_admins': active_admins,
        }

    elif request.user.user_type == 'branch_admin':
        # Get the branch this admin manages
        branch = request.user.managed_branch

        if branch:
            branch_income = branch.get_total_income()
            branch_expenditure = branch.get_total_expenditure()
            branch_balance = branch.get_balance()

            recent_transactions = branch.transactions.select_related(
                'income_category', 'expenditure_category', 'created_by'
            ).order_by('-created_date')[:10]

            context = {
                'branch': branch,
                'branch_income': branch_income,
                'branch_expenditure': branch_expenditure,
                'branch_balance': branch_balance,
                'recent_transactions': recent_transactions,
            }
        else:
            messages.error(request, 'No branch assigned to your account. Please contact the administrator.')
            context = {
                'error_message': 'No branch assigned to your account. Please contact the administrator.',
                'show_contact_info': True,
            }
    else:
        # Handle users without proper user_type
        messages.warning(request, 'Your account needs to be configured. Please contact the administrator.')
        context = {
            'info_message': 'Your account is being set up. Please contact the administrator.',
            'show_contact_info': True,
        }

    return render(request, 'home.html', context)


@login_required
def create_branch(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can create branches.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = BranchForm(request.POST)

        if form.is_valid():
            branch = form.save(commit=False)
            branch.created_by = request.user
            try:
                branch.save()
                messages.success(request, f'Branch "{branch.name}" created successfully!')
                return redirect('manage_branches')
            except Exception as e:
                messages.error(request, f'Error creating branch: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BranchForm()

    return render(request, 'create_branch.html', {'form': form})


@login_required
def create_branch_admin(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can create branch admins.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = BranchAdminForm(request.POST)

        if form.is_valid():
            admin_user = form.save()
            messages.success(request, f'Branch admin "{admin_user.get_full_name()}" created successfully!')
            return redirect('manage_users')
    else:
        form = BranchAdminForm()

    return render(request, 'create_branch_admin.html', {'form': form})


@login_required
def manage_users(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can manage users.')
        return redirect('dashboard')

    users = User.objects.filter(user_type='branch_admin').order_by('-date_joined')
    return render(request, 'manage_users.html', {'users': users})


@login_required
def manage_branches(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can manage branches.')
        return redirect('dashboard')

    branches = Branch.objects.all().select_related('created_by').prefetch_related('admins').order_by('-created_date')
    return render(request, 'manage_branches.html', {'branches': branches})


@login_required
def assign_branch_admin(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can assign branch admins.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = BranchAdminAssignmentForm(request.POST)

        if form.is_valid():
            branch = form.cleaned_data['branch']
            admins = form.cleaned_data['admins']

            # Clear existing assignments for this branch
            branch.admins.clear()

            # Add new assignments
            for admin in admins:
                branch.admins.add(admin)

            admin_names = ', '.join([admin.get_full_name() for admin in admins])
            messages.success(request, f'Admins ({admin_names}) assigned to "{branch.name}" successfully!')
            return redirect('manage_branches')
    else:
        form = BranchAdminAssignmentForm()

    return render(request, 'assign_branch_admin.html', {'form': form})


@login_required
def allocate_funds(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can allocate funds.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = FundAllocationForm(request.POST, user=request.user)

        if form.is_valid():
            fund_allocation = form.save(commit=False)
            main_branch = Branch.objects.filter(branch_type='main').first()
            if not main_branch:
                messages.error(request, 'Main branch not found. Please create a main branch first.')
                return render(request, 'allocate_funds.html', {'form': form})

            fund_allocation.from_branch = main_branch
            fund_allocation.allocated_by = request.user

            # Update branch allocated funds
            to_branch = fund_allocation.to_branch
            to_branch.allocated_funds += fund_allocation.amount
            to_branch.save()

            fund_allocation.save()

            # Get or create default categories for fund allocation
            income_category, created = IncomeCategory.objects.get_or_create(
                name='Fund Allocation',
                defaults={
                    'description': 'Funds allocated from main branch',
                    'scope': 'all',
                    'created_by': request.user
                }
            )

            expenditure_category, created = ExpenditureCategory.objects.get_or_create(
                name='Fund Allocation',
                defaults={
                    'description': 'Funds allocated to sub branches',
                    'scope': 'all',
                    'created_by': request.user
                }
            )

            # Create income transaction for receiving branch
            Transaction.objects.create(
                branch=to_branch,
                transaction_type='income',
                amount=fund_allocation.amount,
                description=f'Fund allocation received from {main_branch.name}: {fund_allocation.description}',
                date=fund_allocation.allocated_date.date(),
                income_category=income_category,
                fund_allocation=fund_allocation,
                created_by=request.user
            )

            # Create expenditure transaction for main branch (deduction)
            Transaction.objects.create(
                branch=main_branch,
                transaction_type='expenditure',
                amount=fund_allocation.amount,
                description=f'Fund allocation to {to_branch.name}: {fund_allocation.description}',
                date=fund_allocation.allocated_date.date(),
                expenditure_category=expenditure_category,
                fund_allocation=fund_allocation,
                created_by=request.user
            )

            messages.success(request, f'₦{fund_allocation.amount:,.2f} allocated to "{to_branch.name}" successfully!')
            return redirect('fund_allocations')
    else:
        form = FundAllocationForm(user=request.user)

    return render(request, 'allocate_funds.html', {'form': form})


@login_required
def fund_allocations(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can view fund allocations.')
        return redirect('dashboard')

    allocations = FundAllocation.objects.select_related(
        'from_branch', 'to_branch', 'allocated_by'
    ).order_by('-allocated_date')
    return render(request, 'fund_allocations.html', {'allocations': allocations})


@login_required
def transactions(request):
    if request.user.user_type == 'super_admin':
        transactions_list = Transaction.objects.select_related(
            'branch', 'created_by', 'income_category', 'expenditure_category'
        ).filter(branch__is_active=True)
        branches = Branch.objects.filter(is_active=True).order_by('name')
    else:
        branch = request.user.managed_branch
        if not branch:
            messages.error(request, 'No branch assigned to your account.')
            return redirect('dashboard')
        transactions_list = branch.transactions.select_related(
            'created_by', 'income_category', 'expenditure_category'
        )
        branches = None

    # Filter by branch if requested
    branch_filter = request.GET.get('branch')
    if branch_filter and request.user.user_type == 'super_admin':
        transactions_list = transactions_list.filter(branch_id=branch_filter)

    # Filter by type
    type_filter = request.GET.get('type')
    if type_filter:
        transactions_list = transactions_list.filter(transaction_type=type_filter)

    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        transactions_list = transactions_list.filter(date__gte=start_date)
    if end_date:
        transactions_list = transactions_list.filter(date__lte=end_date)

    # Order by date
    transactions_list = transactions_list.order_by('-date', '-created_date')

    # Calculate totals for the filtered transactions
    total_income = transactions_list.filter(transaction_type='income').aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    total_expenditure = transactions_list.filter(transaction_type='expenditure').aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    net_balance = total_income - total_expenditure

    context = {
        'transactions': transactions_list[:100],  # Limit to 100 for performance
        'branches': branches,
        'total_income': total_income,
        'total_expenditure': total_expenditure,
        'net_balance': net_balance,
        'selected_branch': branch_filter,
        'selected_type': type_filter,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'transactions.html', context)


@login_required
def add_transaction(request):
    # Check if branch admin is trying to add income (not allowed)
    if request.user.user_type == 'branch_admin':
        if request.method == 'POST':
            transaction_type = request.POST.get('transaction_type')
            if transaction_type == 'income':
                messages.error(request, 'Branch administrators can only add expenditure transactions. Income can only be added by the main administrator.')
                return redirect('add_transaction')
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user

            # Set branch based on user type
            if request.user.user_type == 'super_admin':
                transaction.branch = form.cleaned_data['branch']
            else:
                branch = request.user.managed_branch
                if not branch:
                    messages.error(request, 'No branch assigned to your account.')
                    return redirect('dashboard')
                transaction.branch = branch

            # Additional balance validation at view level
            if transaction.transaction_type == 'expenditure':
                current_balance = transaction.branch.get_balance()
                if current_balance < transaction.amount:
                    messages.error(request, 
                        f"Insufficient funds. Current balance is ₦{current_balance:,.2f}, "
                        f"but you're trying to spend ₦{transaction.amount:,.2f}. "
                        f"Available balance: ₦{current_balance:,.2f}"
                    )
                    return render(request, 'add_transaction.html', {'form': form})

            transaction.save()
            messages.success(request, 'Transaction added successfully!')
            return redirect('transactions')
    else:
        form = TransactionForm(user=request.user)

    return render(request, 'add_transaction.html', {'form': form})


@login_required
def add_income(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super administrators can add income transactions.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.transaction_type = 'income'  # Force income type
            transaction.branch = form.cleaned_data['branch']

            transaction.save()
            messages.success(request, 'Income transaction added successfully!')
            return redirect('transactions')
    else:
        form = TransactionForm(user=request.user)
        form.fields['transaction_type'].initial = 'income'  # Pre-select income

    return render(request, 'add_transaction.html', {'form': form, 'transaction_type': 'income'})


@login_required
def add_expenditure(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = request.user
            transaction.transaction_type = 'expenditure'  # Force expenditure type

            # Set branch based on user type
            if request.user.user_type == 'super_admin':
                transaction.branch = form.cleaned_data['branch']
            else:
                branch = request.user.managed_branch
                if not branch:
                    messages.error(request, 'No branch assigned to your account.')
                    return redirect('dashboard')
                transaction.branch = branch

            # Additional balance validation at view level
            current_balance = transaction.branch.get_balance()
            if current_balance < transaction.amount:
                messages.error(request, 
                    f"Insufficient funds. Current balance is ₦{current_balance:,.2f}, "
                    f"but you're trying to spend ₦{transaction.amount:,.2f}. "
                    f"Available balance: ₦{current_balance:,.2f}"
                )
                return render(request, 'add_transaction.html', {'form': form, 'transaction_type': 'expenditure'})

            transaction.save()
            messages.success(request, 'Expenditure transaction added successfully!')
            return redirect('transactions')
    else:
        form = TransactionForm(user=request.user)
        form.fields['transaction_type'].initial = 'expenditure'  # Pre-select expenditure

    return render(request, 'add_transaction.html', {'form': form, 'transaction_type': 'expenditure'})


@login_required
def manage_categories(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can manage categories.')
        return redirect('dashboard')

    income_categories = IncomeCategory.objects.select_related('branch', 'created_by').filter(is_active=True)
    expenditure_categories = ExpenditureCategory.objects.select_related('branch', 'created_by').filter(is_active=True)

    return render(request, 'manage_categories.html', {
        'income_categories': income_categories,
        'expenditure_categories': expenditure_categories,
    })


@login_required
def add_income_category(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can create categories.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = IncomeCategoryForm(request.POST, user=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user

            # Super admin can set scope and branch
            branch = form.cleaned_data.get('branch')
            if branch:
                category.branch = branch

            category.save()
            messages.success(request, 'Income category added successfully!')
            return redirect('manage_categories')
    else:
        form = IncomeCategoryForm(user=request.user)

    return render(request, 'add_category.html', {'form': form, 'category_type': 'Income'})


@login_required
def add_expenditure_category(request):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can create categories.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ExpenditureCategoryForm(request.POST, user=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user

            # Super admin can set scope and branch
            branch = form.cleaned_data.get('branch')
            if branch:
                category.branch = branch

            category.save()
            messages.success(request, 'Expenditure category added successfully!')
            return redirect('manage_categories')
    else:
        form = ExpenditureCategoryForm(user=request.user)

    return render(request, 'add_category.html', {'form': form, 'category_type': 'Expenditure'})


# New views for delete functionality and user management

@login_required
def delete_branch(request, branch_id):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can delete branches.')
        return redirect('dashboard')

    branch = get_object_or_404(Branch, id=branch_id)

    if branch.branch_type == 'main':
        messages.error(request, 'Cannot delete the main branch.')
        return redirect('manage_branches')

    if request.method == 'POST':
        branch_name = branch.name
        branch.delete()
        messages.success(request, f'Branch "{branch_name}" deleted successfully!')
        return redirect('manage_branches')

    # Check for related data
    transaction_count = branch.transactions.count()
    allocation_count = branch.fund_allocations_received.count()

    return render(request, 'confirm_delete.html', {
        'object_name': f'Branch "{branch.name}"',
        'object_type': 'branch',
        'related_data': {
            'Transactions': transaction_count,
            'Fund Allocations': allocation_count,
        },
        'warning': 'Deleting this branch will also delete all related transactions and fund allocations.',
        'delete_url': request.path
    })


@login_required
def delete_user(request, user_id):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can delete users.')
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    if user.user_type == 'super_admin':
        messages.error(request, 'Cannot delete super admin users.')
        return redirect('manage_users')

    if request.method == 'POST':
        user_name = user.get_full_name()
        user.delete()
        messages.success(request, f'User "{user_name}" deleted successfully!')
        return redirect('manage_users')

    # Check for related data
    transaction_count = user.transaction_set.count()
    branch_count = user.managed_branches.count()

    return render(request, 'confirm_delete.html', {
        'object_name': f'User "{user.get_full_name()}"',
        'object_type': 'user',
        'related_data': {
            'Transactions': transaction_count,
            'Managed Branches': branch_count,
        },
        'warning': 'Deleting this user will transfer their created transactions to your account.',
        'delete_url': request.path
    })


@login_required
def delete_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id)

    # Check permissions
    if request.user.user_type == 'super_admin':
        pass  # Super admin can delete any transaction
    elif request.user.user_type == 'branch_admin':
        if transaction.branch != request.user.managed_branch:
            messages.error(request, 'You can only delete transactions from your branch.')
            return redirect('transactions')
    else:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        transaction_desc = f'"{transaction.description}" (₦{transaction.amount:,.2f})'
        transaction.delete()
        messages.success(request, f'Transaction {transaction_desc} deleted successfully!')
        return redirect('transactions')

    return render(request, 'confirm_delete.html', {
        'object_name': f'Transaction: {transaction.description}',
        'object_type': 'transaction',
        'details': f'Amount: ₦{transaction.amount:,.2f}, Date: {transaction.date}, Branch: {transaction.branch.name}',
        'warning': 'This action cannot be undone.',
        'delete_url': request.path
    })


@login_required
def toggle_user_status(request, user_id):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can change user status.')
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    if user.user_type == 'super_admin':
        messages.error(request, 'Cannot change status of super admin users.')
        return redirect('manage_users')

    user.is_active = not user.is_active
    user.save()

    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User "{user.get_full_name()}" {status} successfully!')
    return redirect('manage_users')


@login_required
def reset_user_password(request, user_id):
    if request.user.user_type != 'super_admin':
        messages.error(request, 'Only super admin can reset passwords.')
        return redirect('dashboard')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        if len(new_password) < 4:
            messages.error(request, 'Password must be at least 4 characters long.')
            return render(request, 'reset_password.html', {'user': user})

        user.set_password(new_password)
        user.save()

        messages.success(request, f'Password for "{user.get_full_name()}" reset successfully!')
        return redirect('manage_users')

    return render(request, 'reset_password.html', {'user': user})


@login_required
def reports(request):
    from datetime import datetime, timedelta
    from django.db.models import Count, Avg
    
    # Get date range filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    report_type = request.GET.get('report_type', 'overview')
    branch_filter = request.GET.get('branch')
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Convert to date objects for filtering
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Base queryset for transactions in date range
    transactions_qs = Transaction.objects.filter(
        date__range=[start_date_obj, end_date_obj],
        branch__is_active=True
    )
    
    # Filter by user type and branch
    if request.user.user_type == 'super_admin':
        # Super admin can see all branches or filter by specific branch
        branches = Branch.objects.filter(is_active=True).order_by('name')
        if branch_filter:
            transactions_qs = transactions_qs.filter(branch_id=branch_filter)
    else:
        # Branch admin can only see their own branch
        branch = request.user.managed_branch
        if branch:
            transactions_qs = transactions_qs.filter(branch=branch)
        else:
            transactions_qs = Transaction.objects.none()
        branches = None
    
    # Calculate financial metrics
    total_income = transactions_qs.filter(transaction_type='income').aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    total_expenditure = transactions_qs.filter(transaction_type='expenditure').aggregate(
        Sum('amount'))['amount__sum'] or Decimal('0')
    net_balance = total_income - total_expenditure
    
    # Transaction counts
    income_count = transactions_qs.filter(transaction_type='income').count()
    expenditure_count = transactions_qs.filter(transaction_type='expenditure').count()
    total_transactions = income_count + expenditure_count
    
    # Calculate average transaction value
    average_transaction_value = Decimal('0')
    if total_transactions > 0:
        total_amount = total_income + total_expenditure
        average_transaction_value = total_amount / total_transactions
    
    # Daily transaction trends (last 30 days)
    daily_trends = []
    for i in range(30):
        date = datetime.now().date() - timedelta(days=i)
        day_income = transactions_qs.filter(
            transaction_type='income', 
            date=date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        day_expenditure = transactions_qs.filter(
            transaction_type='expenditure', 
            date=date
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        daily_trends.append({
            'date': date,
            'income': day_income,
            'expenditure': day_expenditure,
            'net': day_income - day_expenditure
        })
    
    # Top categories
    income_categories = transactions_qs.filter(transaction_type='income').values(
        'income_category__name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    expenditure_categories = transactions_qs.filter(transaction_type='expenditure').values(
        'expenditure_category__name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:5]
    
    # Branch performance (super admin only)
    branch_performance = []
    if request.user.user_type == 'super_admin':
        branches = Branch.objects.filter(is_active=True)
        for branch in branches:
            branch_transactions = transactions_qs.filter(branch=branch)
            branch_income = branch_transactions.filter(transaction_type='income').aggregate(
                Sum('amount'))['amount__sum'] or Decimal('0')
            branch_expenditure = branch_transactions.filter(transaction_type='expenditure').aggregate(
                Sum('amount'))['amount__sum'] or Decimal('0')
            branch_performance.append({
                'branch': branch,
                'income': branch_income,
                'expenditure': branch_expenditure,
                'net': branch_income - branch_expenditure,
                'transaction_count': branch_transactions.count()
            })
    
    # Recent transactions
    recent_transactions = transactions_qs.select_related(
        'branch', 'created_by', 'income_category', 'expenditure_category'
    ).order_by('-created_date')[:10]
    
    # Monthly comparison (current vs previous month)
    current_month_start = datetime.now().replace(day=1).date()
    previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    previous_month_end = current_month_start - timedelta(days=1)
    
    current_month_income = transactions_qs.filter(
        transaction_type='income',
        date__gte=current_month_start
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    previous_month_income = Transaction.objects.filter(
        transaction_type='income',
        date__range=[previous_month_start, previous_month_end],
        branch__is_active=True
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    income_growth = 0
    if previous_month_income > 0:
        income_growth = ((current_month_income - previous_month_income) / previous_month_income) * 100
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'report_type': report_type,
        'branches': branches,
        'selected_branch': branch_filter,
        'total_income': total_income,
        'total_expenditure': total_expenditure,
        'net_balance': net_balance,
        'income_count': income_count,
        'expenditure_count': expenditure_count,
        'total_transactions': total_transactions,
        'average_transaction_value': average_transaction_value,
        'daily_trends': daily_trends,
        'income_categories': income_categories,
        'expenditure_categories': expenditure_categories,
        'branch_performance': branch_performance,
        'recent_transactions': recent_transactions,
        'current_month_income': current_month_income,
        'previous_month_income': previous_month_income,
        'income_growth': income_growth,
    }
    
    return render(request, 'reports.html', context)
