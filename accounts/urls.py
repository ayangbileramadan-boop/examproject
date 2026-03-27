from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/student/', views.student_signup, name='student_signup'),
    path('signup/instructor/', views.instructor_signup, name='instructor_signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    # Password Reset URLs
    path('password-reset/request/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),
]





from django.urls import path
from your_app.views import create_admin

urlpatterns = [
    path('create-admin/', create_admin),
]
