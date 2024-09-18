from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("app/", include("app.urls")),
    path("blog/", include("blog.urls")),
    path("chat/", include("chat.urls")),
    path("melon/", include("melon.urls")),
    path("", TemplateView.as_view(
        template_name="root.html",
        extra_context={"ncp_map_client_id": settings.NCP_MAP_CLIENT_ID}
    ), name="root"),
]
