from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_STUDENT = 'student'
    ROLE_INSTRUCTOR = 'instructor'
    ROLE_ADMIN = 'admin'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_INSTRUCTOR, 'Instructor'),
        (ROLE_ADMIN, 'Admin'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    is_approved = models.BooleanField(default=False, help_text="Instructors must be approved by admin")
    department = models.CharField(max_length=100, blank=True)
    staff_id = models.CharField(max_length=50, blank=True)
    full_name = models.CharField(max_length=150, blank=True)
    avatar_initials = models.CharField(max_length=3, blank=True)

    def save(self, *args, **kwargs):
        # Students are auto-approved; instructors need admin approval
        if self.role == self.ROLE_STUDENT:
            self.is_approved = True
        # Auto-generate avatar initials
        name = self.full_name or self.username
        parts = name.split()
        if len(parts) >= 2:
            self.avatar_initials = (parts[0][0] + parts[-1][0]).upper()
        elif name:
            self.avatar_initials = name[:2].upper()
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.ROLE_STUDENT

    @property
    def is_instructor(self):
        return self.role == self.ROLE_INSTRUCTOR

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.username} ({self.role})"
