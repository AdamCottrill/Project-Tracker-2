from django.conf import settings
from django.conf.urls import url, include
from django.urls import path, re_path
from rest_framework import routers
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.permissions import AllowAny

from drf_yasg import openapi
from drf_yasg.views import get_schema_view

from .views import (
    UserViewSet,
    ProjectViewSet,
    ProjectTypeViewSet,
    ProjectPointViewSet,
    ProjectPolygonViewSet,
    ProjectAbstractViewSet,
    points_roi,
    ReportListView,
    AssociatedFilesListView,
)

app_name = "api"

PRJ_CD_REGEX = settings.PRJ_CD_REGEX

API_TITLE = "Project Tracker API"
API_DESC = "A Restful API Project Tracker Data"


router = routers.DefaultRouter()

router.register(r"projects", ProjectViewSet)
router.register(r"project_leads", UserViewSet, basename="project_lead")
router.register(r"project_types", ProjectTypeViewSet, basename="project_type")
router.register(
    r"project_abstracts", ProjectAbstractViewSet, basename="project_abstract"
)

urlpatterns = [
    #    url(
    #        r"^project_abstracts/",
    #        ProjectAbstractViewSet.as_view({"get": "list"}),
    #        name="project_abstracts",
    #    ),
    url(
        r"^project_points/" + PRJ_CD_REGEX,
        ProjectPointViewSet.as_view({"get": "list"}),
        name="project_points",
    ),
    url(
        r"^project_polygon/" + PRJ_CD_REGEX,
        ProjectPolygonViewSet.as_view({"get": "list"}),
        name="project_polygon",
    ),
    # just the points - regardless of project
    url(r"points_in_roi/", points_roi, {"how": "points_in"}, name="get_points_in_roi"),
    # points for projects were ALL points are in roi
    url(
        r"project_points_contained_in_roi/",
        points_roi,
        {"how": "contained"},
        name="get_project_points_contained_in_roi",
    ),
    # points for projects were SOME points are in roi
    url(
        r"project_points_overlapping_roi/",
        points_roi,
        {"how": "overlapping"},
        name="get_project_points_overlapping_roi",
    ),
    url(
        r"^reports/",
        ReportListView.as_view(),
        name="reports_list",
    ),
    url(
        r"^associated_files/",
        AssociatedFilesListView.as_view(),
        name="associated_files_list",
    ),
    url(r"^", include(router.urls)),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]


# urlpatterns = format_suffix_patterns(urlpatterns)

schema_view = get_schema_view(
    openapi.Info(
        title=API_TITLE,
        default_version="v1",
        description=API_DESC,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="adam.cottrill@ontario.ca"),
        license=openapi.License(name="BSD License"),
    ),
    # generate docs for all endpoint from here down:
    patterns=urlpatterns,
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns += [
    # =============================================
    #          API AND DOCUMENTATION
    # api documentation
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
