from django.contrib import admin

from .forms import MemberDuplicateCheckForm
from .models import Member


class MembershipReviewAdmin(admin.ModelAdmin):
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Member)
class MemberAccountAdmin(MembershipReviewAdmin):
    form = MemberDuplicateCheckForm
    fields = ("member_id", "family_name", "first_name", "middle_name", "account")
    readonly_fields = ("member_id", "family_name", "first_name", "middle_name")
    list_display = ("member_id", "family_name", "first_name", "username")
    search_fields = ("family_name", "first_name")
    autocomplete_fields = ("account",)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("family_name", "first_name", "middle_name", "birth_date", "contact_numbers", "account")
        return super().get_fields(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return super().get_readonly_fields(request, obj)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Username", ordering="account__username")
    def username(self, member):
        return member.account.get_username() if member.account_id else None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account":
            kwargs["label"] = "Username"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

