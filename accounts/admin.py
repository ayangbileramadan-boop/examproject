from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'is_approved', 'is_superuser', 'department', 'date_joined']
    list_filter = ['role', 'is_approved', 'is_active', 'is_superuser']
    list_editable = ['is_approved']
    search_fields = ['username', 'email', 'full_name', 'staff_id']
    fieldsets = UserAdmin.fieldsets + (
        ('ExamSystem Info', {
            'fields': ('role', 'is_approved', 'full_name', 'department', 'staff_id', 'avatar_initials')
        }),
    )
    actions = ['approve_instructors', 'revoke_approval', 'make_admin', 'remove_admin']

    def approve_instructors(self, request, queryset):
        updated = queryset.filter(role='instructor').update(is_approved=True)
        self.message_user(request, f"{updated} instructor(s) approved.")
    approve_instructors.short_description = "Approve selected instructors"

    def revoke_approval(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} account(s) approval revoked.")
    revoke_approval.short_description = "Revoke approval"

    def make_admin(self, request, queryset):
        updated = queryset.update(role='admin')
        self.message_user(request, f"{updated} user(s) set as admin.")
    make_admin.short_description = "Set selected users as Admin"

    def remove_admin(self, request, queryset):
        updated = queryset.update(role='student')
        self.message_user(request, f"{updated} user(s) demoted to student.")
    remove_admin.short_description = "Demote to Student"
