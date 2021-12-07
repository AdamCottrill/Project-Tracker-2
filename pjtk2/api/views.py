from django.db.models import Q, Prefetch, F
from django.http import Http404
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry, Polygon

from rest_framework import generics, viewsets, status
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.response import Response

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS

from django_filters import rest_framework as filters

from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError


from .serializers import (
    ProjectSerializer,
    ProjectAbstractSerializer,
    ProjectTypeSerializer,
    ProjectPointSerializer,
    ProjectPolygonSerializer,
    UserSerializer,
    ReportSerializer,
    AssociatedFileSerializer,
)
from pjtk2.models import (
    Project,
    ProjectType,
    SamplePoint,
    ProjectPolygon,
    ProjectImage,
    Report,
    AssociatedFile,
)

from pjtk2.filters import (
    SamplePointFilter,
    ProjectFilter,
    AssociatedFileFilter,
    ReportFilter,
)

from pjtk2.utils.spatial_utils import find_roi_points

User = get_user_model()


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 500
    page_size_query_param = "page_size"
    max_page_size = 1000


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.order_by("id").all()
    serializer_class = UserSerializer
    pagination_class = StandardResultsSetPagination
    lookup_field = "username"


class ProjectTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProjectType.objects.order_by("id").all()
    serializer_class = ProjectTypeSerializer
    pagination_class = StandardResultsSetPagination


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    pagination_class = StandardResultsSetPagination
    lookup_field = "slug"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ProjectFilter


class ProjectAbstractViewSet(viewsets.ReadOnlyModelViewSet):
    """A read only endpoint that returns the data need to create the UGLMU
    annual Assessment Report."""

    queryset = (
        Project.objects.filter(cancelled=False, active=True)
        .select_related("project_type", "prj_ldr")
        .prefetch_related(
            Prefetch("images", queryset=ProjectImage.objects.filter(report=True))
        )
        .order_by("-year", "project_type__project_type", "prj_nm")
    )
    serializer_class = ProjectAbstractSerializer
    pagination_class = StandardResultsSetPagination
    lookup_field = "slug"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ProjectFilter

    # def get_queryset(self):
    #     queryset = super(ProjectAbstractListView, self).get_queryset()
    #     slug = self.kwargs.get("slug")
    #     if slug:
    #         return queryset.filter(project__slug=slug.lower())
    #     else:
    #         return queryset


class ProjectPointViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = SamplePoint.objects.select_related("project", "project__project_type")
    serializer_class = ProjectPointSerializer
    pagination_class = None

    def get_queryset(self):

        queryset = super(ProjectPointViewSet, self).get_queryset()
        slug = self.kwargs.get("slug").lower()
        return queryset.filter(project__slug=slug)


class ProjectPolygonViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ProjectPolygonSerializer

    def get_queryset(self):
        slug = self.kwargs.get("slug").lower()
        return ProjectPolygon.objects.filter(project__slug=slug)


@api_view(["POST"])
@permission_classes((AllowAny,))
def points_roi(request, how="contained"):
    """A view to return all of the sampling points either contained in or
    overlapping the region of interest.  Overlapping projects will have at
    least one point in the region of interest.

    The argument 'how' determines whether we return points from
    projects that were completely contained in the region of interest
    or have some of their samples in the region of interest.

    """

    first_year = request.GET.get("first_year")
    last_year = request.GET.get("last_year")
    project_types = request.GET.get("project_type")

    # get the region of interest from the request - raise an error if we can't
    request_roi = request.GET.get("roi")
    if request_roi is None:
        request_roi = request.POST.get("roi")
        if request_roi is None:
            raise Http404

    # convert the roi string to a geos object
    try:
        roi = GEOSGeometry(request_roi)
    except ValueError:
        errmsg = "roi could not be converted to a valid GEOS geometry."
        raise ValidationError(errmsg)

    # try to create a polygon from our region of interest.
    # and  Raise a TypeError if roi is not a valid Linear Ring or Polygon
    if roi.geom_type not in ("Polygon", "MultiPolygon"):
        try:
            roi = Polygon(roi)
        except TypeError:
            errmsg = "roi is not a valid polygon."
            raise ValidationError(errmsg)

    if how == "points_in":
        # return all of the sample points in the roi
        sample_points = (
            SamplePoint.objects.select_related("project", "project__project_type")
            .filter(geom__within=roi)
            .order_by()
        )

    elif how == "contained":
        # return only points from projects that are completely contained within the roi
        sample_points = (
            SamplePoint.objects.select_related("project", "project__project_type")
            .filter(project__multipoints__geom__within=roi)
            .order_by()
        )
    else:
        project_ids = (
            Project.objects.filter(multipoints__geom__intersects=roi)
            .exclude(multipoints__geom__within=roi)
            .values_list("id")
            .distinct()
        )
        sample_points = (
            SamplePoint.objects.select_related("project", "project__project_type")
            .filter(project__pk__in=project_ids)
            .order_by()
        )
        # If we want to clip our points to just those in the region, do it here:
        # sample_points = sample_points.filter(geom__within=roi)

    if project_types:
        sample_points = sample_points.filter(
            project__project_type__pk__in=project_types.split(",")
        )

    if first_year:
        sample_points = sample_points.filter(project__year__gte=first_year)

    if last_year:
        sample_points = sample_points.filter(project__year__lte=last_year)

    serializer = ProjectPointSerializer(
        sample_points, many=True, context={"request": request}
    )

    # if how == "points_in":
    #     # we just want the points in the ROI, regardless of project.
    #     sample_points = (
    #         SamplePoint.objects.filter(geom__within=roi)
    #         .select_related("project")
    #         .order_by("-project__year", "label")
    #     )
    #     sample_point_filter = SamplePointFilter(request.GET, sample_points)
    #     serializer = ProjectPointSerializer(
    #         sample_point_filter.qs, many=True, context={"request": request}
    #     )

    # else:
    #     # get the unique project codes for all of the points that fall in
    #     # the region of interest
    #     sample_points = (
    #         SamplePoint.objects.filter(geom__within=roi)
    #         .select_related("project")
    #         .distinct("project__prj_cd", "project__year")
    #         .values_list("project__prj_cd")
    #         .order_by("-project__year")
    #     )

    #     # use django-filter to parse any url parameters and filter our
    #     # results accordingly.
    #     sample_point_filter = SamplePointFilter(request.GET, sample_points)

    #     # get our list of unique project codes after filtering:
    #     prj_cds = [x[0] for x in sample_point_filter.qs]
    #     points = find_roi_points(roi, prj_cds)

    #     # serialize the points based on the value of 'how' (either 'overlapping' or
    #     #'contained'):
    #     serializer = ProjectPointSerializer(
    #         points[how], many=True, context={"request": request}
    #     )

    return Response(serializer.data)


class SamplePointListView(ListAPIView):
    """A read-only endpoint to return sampling points."""

    serializer_class = ProjectPointSerializer
    permission_classes = [ReadOnly]
    pagination_class = LargeResultsSetPagination
    filterset_class = SamplePointFilter
    queryset = SamplePoint.objects.select_related(
        "project", "project__project_type"
    ).all()


class ReportListView(ListAPIView):
    """A read-only endpoint to return currently available reports."""

    serializer_class = ReportSerializer
    permission_classes = [ReadOnly]
    pagination_class = LargeResultsSetPagination
    filterset_class = ReportFilter

    def get_queryset(self):
        """ """
        queryset = (
            Report.objects.filter(current=True, report_path__isnull=False)
            .annotate(
                prj_cd=F("projectreport__project__prj_cd"),
                prj_nm=F("projectreport__project__prj_nm"),
                report_type=F("projectreport__milestone__label_abbrev"),
                _uploaded_by=F("uploaded_by__username"),
            )
            .values(
                "prj_cd",
                "prj_nm",
                "report_type",
                "current",
                "report_path",
                "uploaded_on",
                "_uploaded_by",
            )
        )

        return queryset


class AssociatedFilesListView(ListAPIView):
    """A read-only endpoint to return associated files."""

    serializer_class = AssociatedFileSerializer
    permission_classes = [ReadOnly]
    pagination_class = LargeResultsSetPagination
    filterset_class = AssociatedFileFilter

    def get_queryset(self):
        """ """
        queryset = (
            AssociatedFile.objects.filter(current=True)
            .annotate(
                prj_cd=F("project__prj_cd"),
                prj_nm=F("project__prj_nm"),
                _uploaded_by=F("uploaded_by__username"),
            )
            .values(
                "prj_cd",
                "prj_nm",
                "current",
                "file_path",
                "uploaded_on",
                "_uploaded_by",
            )
        )

        return queryset
