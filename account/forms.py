from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from .models import *
from .validators import validate_minimum_length
from django.db.models import Sum, Q


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'location', 'state', 'address', 'branch_type', 'allocated_funds']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'required': True}),
            'branch_type': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'allocated_funds': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default value for allocated_funds if not provided
        if not self.instance.pk and 'allocated_funds' not in self.data:
            self.fields['allocated_funds'].initial = 0

class BranchAdminForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_first_name'}))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_last_name'}))
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_username', 'placeholder': 'Will be generated from first and last name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'minlength': '4'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'minlength': '4'}))

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return password2

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        if password1 and len(password1) < 4:
            raise forms.ValidationError("Password must be at least 4 characters long.")
        return password1

    def save(self):
        # Create user manually without Django's complex validation
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data.get('phone', ''),
            user_type='branch_admin'
        )
        return user

class BranchAdminAssignmentForm(forms.Form):
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    admins = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(user_type='branch_admin'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )

class FundAllocationForm(forms.ModelForm):
    class Meta:
        model = FundAllocation
        fields = ['to_branch', 'amount', 'description']
        widgets = {
            'to_branch': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.user_type == 'super_admin':
            # Only show sub branches for allocation
            self.fields['to_branch'].queryset = Branch.objects.filter(
                is_active=True,
                branch_type='sub'
            )

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'description', 'date', 'income_category', 'expenditure_category']
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'income_category': forms.Select(attrs={'class': 'form-control'}),
            'expenditure_category': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            if user.user_type == 'super_admin':
                self.fields['branch'] = forms.ModelChoiceField(
                    queryset=Branch.objects.filter(is_active=True),
                    widget=forms.Select(attrs={'class': 'form-control'}),
                    required=True
                )
                # Super admin can see all categories
                income_categories = IncomeCategory.objects.filter(is_active=True)
                expenditure_categories = ExpenditureCategory.objects.filter(is_active=True)
            else:
                # Branch admin sees categories available to their branch
                branch = user.managed_branch
                if branch:
                    income_categories = IncomeCategory.objects.filter(
                        Q(scope__in=['all', branch.branch_type]) | Q(branch=branch),
                        is_active=True
                    )
                    expenditure_categories = ExpenditureCategory.objects.filter(
                        Q(scope__in=['all', branch.branch_type]) | Q(branch=branch),
                        is_active=True
                    )
                else:
                    income_categories = IncomeCategory.objects.none()
                    expenditure_categories = ExpenditureCategory.objects.none()

            self.fields['income_category'].queryset = income_categories
            self.fields['expenditure_category'].queryset = expenditure_categories

class IncomeCategoryForm(forms.ModelForm):
    class Meta:
        model = IncomeCategory
        fields = ['name', 'description', 'scope']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scope': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.user_type == 'super_admin':
            self.fields['branch'] = forms.ModelChoiceField(
                queryset=Branch.objects.filter(is_active=True),
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=False,
                help_text='Leave empty for global categories'
            )

class ExpenditureCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenditureCategory
        fields = ['name', 'description', 'scope']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scope': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.user_type == 'super_admin':
            self.fields['branch'] = forms.ModelChoiceField(
                queryset=Branch.objects.filter(is_active=True),
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=False,
                help_text='Leave empty for global categories'
            )
