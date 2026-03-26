from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    # Public
    path('', views.landing, name='landing'),
    path('home/', views.landing_page, name='landing_page'),

    # Student
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('join/', views.join_exam, name='join_exam'),
    path('exam/<int:pk>/take/', views.take_exam, name='take_exam'),
    path('exam/<int:pk>/result/', views.exam_result, name='exam_result'),
    path('results/', views.my_results, name='my_results'),

    # Instructor
    path('instructor/', views.instructor_dashboard, name='instructor_dashboard'),
    path('instructor/exam/create/', views.create_exam, name='create_exam'),
    path('instructor/exam/<int:pk>/manage/', views.manage_exam, name='manage_exam'),
    path('instructor/exam/<int:pk>/delete/', views.delete_exam, name='delete_exam'),
    path('instructor/exam/<int:pk>/analytics/', views.exam_analytics, name='exam_analytics'),
    path('instructor/essay/<int:answer_pk>/grade/', views.grade_essay, name='grade_essay'),

    # Admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('user/<int:user_id>/manage/', views.manage_user, name='manage_user'),
]
