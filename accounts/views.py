from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .forms import StudentSignupForm, InstructorSignupForm, LoginForm
from .models import User


def student_signup(request):
    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Explicitly set the backend for authentication
            from django.contrib.auth.backends import ModelBackend
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account is ready.")
            # Use exams namespace for dashboard redirect
            from django.urls import reverse
            return redirect('exams:student_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    return redirect('exams:landing')


def instructor_signup(request):
    if request.method == 'POST':
        form = InstructorSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Request submitted! We'll review and approve your account within 24–48 hours.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    return redirect('exams:landing')


def login_view(request):
    if request.user.is_authenticated:
        return _redirect_dashboard(request.user)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        # Allow login with email
        if '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                pass
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_instructor and not user.is_approved:
                messages.error(request, "Your instructor account is pending admin approval.")
                return redirect('exams:landing')
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return _redirect_dashboard(user)
        else:
            messages.error(request, "Invalid username or password.")
    return redirect('exams:landing')


def logout_view(request):
    logout(request)
    messages.success(request, "You've been logged out.")
    return redirect('exams:landing')


def _redirect_dashboard(user):
    if user.is_admin:
        return redirect('exams:admin_dashboard')
    if user.is_instructor:
        return redirect('exams:instructor_dashboard')
    return redirect('exams:student_dashboard')


# ─── PROFILE & SETTINGS ───────────────────────────────────────────────────────

@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        # Update profile info
        user.full_name = request.POST.get('full_name', '')
        user.email = request.POST.get('email', user.email)
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('accounts:profile')
    
    context = {
        'user': user,
    }
    return render(request, 'profile.html', context)


@login_required
def settings(request):
    user = request.user
    password_form = PasswordChangeForm(user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_password':
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully!")
                return redirect('accounts:settings')
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{error}")
        
        elif action == 'update_profile':
            user.full_name = request.POST.get('full_name', '')
            user.email = request.POST.get('email', user.email)
            if user.is_instructor:
                user.department = request.POST.get('department', '')
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('accounts:settings')
    
    context = {
        'user': user,
        'password_form': password_form,
        'show_department': user.is_instructor,
    }
    return render(request, 'settings.html', context)




def password_reset_request(request):
    """Handle password reset request - send email with reset link"""
    if request.user.is_authenticated:
        return _redirect_dashboard(request.user)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            user = User.objects.get(email=email)
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = request.build_absolute_uri(
                f"/accounts/password-reset/confirm/{uid}/{token}/"
            )
            
            # Send email
            subject = '🔐 Reset Your ExamSystem Password'
            message = f"""
Hello {user.username},

We received a request to reset your password. Click the link below to create a new password:

{reset_url}

If you didn't request this, please ignore this email. Your password will remain unchanged.

This link will expire in 48 hours.

Best regards,
ExamSystem Team
"""
            
            # Print reset link to console for debugging
            print(f"\n{'='*60}")
            print(f"PASSWORD RESET LINK FOR {email}:")
            print(f"{reset_url}")
            print(f"{'='*60}\n")
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                print(f"Email sent successfully to {user.email}")
            except Exception as e:
                print(f"Email error: {e}")
            
            messages.success(request, "Password reset link sent! Check your email.")
                
        except User.DoesNotExist:
            # Don't reveal if email exists
            messages.success(request, "If an account exists with this email, we've sent a reset link.")
        
        return redirect('exams:landing')
    
    return render(request, 'password_reset_request.html')


def password_reset_confirm(request, uidb64, token):
    """Handle password reset confirmation - show new password form"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            
            if password1 != password2:
                messages.error(request, "Passwords don't match.")
            elif len(password1) < 6:
                messages.error(request, "Password must be at least 6 characters.")
            else:
                user.set_password(password1)
                user.save()
                messages.success(request, "Password reset successful! You can now login with your new password.")
                return redirect('exams:landing')
        
        return render(request, 'password_reset_confirm.html', {
            'uidb64': uidb64,
            'token': token,
            'user': user
        })
    else:
        messages.error(request, "Invalid or expired reset link. Please request a new one.")
        return redirect('exams:landing')


def password_reset_done(request):
    """Show password reset done page"""
    return render(request, 'password_reset_done.html')


def password_reset_complete(request):
    """Show password reset complete page"""
    return render(request, 'password_reset_complete.html')




from django.http import HttpResponse
from django.contrib.auth import get_user_model

def create_admin(request):
    User = get_user_model()

    username = "makaveli"
    password = "makaveli456"  # change this!
    email = "makaveli@gmail.com"

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        return HttpResponse("Superuser created!")

    return HttpResponse("Superuser already exists.")
