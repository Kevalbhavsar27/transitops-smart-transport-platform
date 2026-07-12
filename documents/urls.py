from django.urls import path

from . import views


app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="document_list"),
    path("upload/", views.document_create, name="document_create"),
    path(
        "<int:pk>/download/",
        views.document_download,
        name="document_download",
    ),
    path(
        "<int:pk>/delete/",
        views.document_delete,
        name="document_delete",
    ),
]
