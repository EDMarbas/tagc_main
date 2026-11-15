from django.urls import path

from . import views


app_name = "members"
urlpatterns = [
    path("", views.directory, name="directory"),
    path("add/", views.add, name="add"),
    path("add/bulk/", views.bulk_import_members, name="bulk_import"),
    path(
        "add/bulk/template/",
        views.download_member_import_template,
        name="download_member_import_template",
    ),
    path("summary/", views.summary, name="summary"),
    path("notifications/", views.notifications, name="notifications"),
    path("verification/", views.verification_queue, name="verification_queue"),
    path("verification/<int:pk>/", views.review_membership_check, name="review_membership_check"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/<int:pk>/delete/", views.dismiss_notification, name="dismiss_notification"),
    path("me/", views.my_membership, name="my_membership"),
    path("me/apply/", views.my_membership_apply, name="my_membership_apply"),
    path("me/edit/", views.my_membership_edit, name="my_membership_edit"),
    path("me/photo/", views.my_membership_photo, name="my_membership_photo"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("<int:pk>/status/", views.update_member_status, name="update_member_status"),
    path("<int:pk>/photo/", views.photo, name="photo"),
]
