import warnings


from django.urls import include, path, re_path

from django.conf import settings
from django.contrib import admin
from django.views.static import serve as serve_static
from django.contrib.auth import views as authviews

warnings.simplefilter("error", DeprecationWarning)

from pjtk2.views import project_list

admin.autodiscover()

urlpatterns = [
    path("", project_list, name="home"),
    path("", project_list, name="index"),
    path("admin/doc/", include("django.contrib.admindocs.urls")),
    path("coregonusclupeaformis/admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path(
        "accounts/password-change/",
        authviews.PasswordChangeView.as_view(),
        name="change_password",
    ),
    path(
        "accounts/password-change/done/",
        authviews.PasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("projects/", include("pjtk2.urls")),
    re_path(
        r"static/(?P<path>.*)$", serve_static, {"document_root": settings.STATIC_ROOT}
    ),
    re_path(
        r"uploads/(?P<path>.*)$", serve_static, {"document_root": settings.MEDIA_ROOT}
    ),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
