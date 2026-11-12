from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User

from .models import Activity, ManagementEntry, Organization, ReviewEntry, Track
from .permissions import is_reviewer


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "verified", "website"]
    filter_horizontal = ["members"]
    search_fields = ["name"]
    readonly_fields = [field.name for field in Organization._meta.fields] + ["members"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "status", "revision"]
    list_filter = ["status", "kind"]
    # Workflow changes go through the same application authorization and audit.
    readonly_fields = [field.name for field in Activity._meta.fields]
    readonly_fields += [field.name for field in Activity._meta.many_to_many]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReviewEntry)
class ReviewEntryAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in ReviewEntry._meta.fields]
    list_display = ["activity", "author", "action", "revision", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in Track._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return is_reviewer(request.user) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


class ServerOwnerOnly:
    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission

    def has_add_permission(self, request):
        return request.user.is_superuser


admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.register(User, type("ServerUserAdmin", (ServerOwnerOnly, UserAdmin), {}))
admin.site.register(Group, type("ServerGroupAdmin", (ServerOwnerOnly, GroupAdmin), {}))


@admin.register(ManagementEntry)
class ManagementEntryAdmin(admin.ModelAdmin):
    readonly_fields = [field.name for field in ManagementEntry._meta.fields]
    list_display = ["action", "actor", "subject", "organization", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
