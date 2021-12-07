from django import forms
from django.db import models
from django.contrib.gis.geos import GEOSGeometry
import django_filters

from pjtk2.models import Project, ProjectType, SamplePoint, Report, AssociatedFile
from common.models import Lake

# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Layout, Field, Submit


class GeomFilter(django_filters.CharFilter):
    pass


class ValueInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


def get_year_choices():
    """a little helper function to get a distinct list of years that can
    be used for the years filter.  The function returns a list of two
    element tuples.  the first tuple is an empty string and its
    indicator, the remaining tuples are each of the distinct years in
    Projects, sorted in reverse chronological order.
    """
    years = Project.objects.values_list("year")
    years = list(set([x[0] for x in years]))
    years.sort(reverse=True)
    years = [(x, x) for x in years]
    years.insert(0, ("", "---------"))
    return years


class GeoFilterSet(django_filters.FilterSet):
    """A fitlerset class that includes a filter_roi method"""

    def filter_roi(self, queryset, name, value):
        """A custom filter for our region of interest, only return objects
        that have all of there sampling points in the region of interest.
        The region of interest is contained in the 'value' parameter and must be string
        that can be converted to a GEOS geometry, typically wkt or geojson.
        """

        if not value:
            return queryset
        try:
            roi = GEOSGeometry(value, srid=4326)
            geofilter = {}
            geofilter[name] = roi
            queryset = queryset.filter(**geofilter)
        except ValueError:
            pass
        return queryset

    def filter_point(self, queryset, name, value):
        """A custom filter for points.  value must be a string that can be
        converted to a geospoint objects, typically geojson or well
        known text. Optionally followed by a radius in meters to buffer the
        point by. If no radius is provided, a value of 5000 m will be
        assumed.

        POINT(-81.5 45.5);5000

        """

        utm_srid = 26917

        if not value:
            return queryset
        try:
            if "[" in value:
                geom, radius = value.split("[")
                radius = int(radius.replace("]", ""))
            else:
                geom = value
                radius = 5000

            print("radius={}".format(radius))

            pt = GEOSGeometry(geom, srid=4326)
            pt.transform(utm_srid)
            roi = pt.buffer(radius)
            roi.transform(4326)
            geofilter = {}
            geofilter[name] = roi

            queryset = queryset.filter(**geofilter)
        except ValueError:
            pass
        return queryset


class ProjectFilter(GeoFilterSet):
    """A filter for project lists"""

    within__roi = GeomFilter(
        field_name="multipoints__geom__within", method="filter_roi"
    )
    intersects__roi = GeomFilter(
        field_name="multipoints__geom__intersects", method="filter_roi"
    )

    within__buffered_point = GeomFilter(
        field_name="multipoints__geom__within", method="filter_point"
    )
    intersects__buffered_point = GeomFilter(
        field_name="multipoints__geom__intersects", method="filter_point"
    )

    project_type = ValueInFilter(field_name="project_type__id", lookup_expr="in")
    scope = ValueInFilter(field_name="project_type__scope", lookup_expr="in")

    year = django_filters.CharFilter(field_name="year", lookup_expr="exact")
    year__gte = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    year__lte = django_filters.NumberFilter(field_name="year", lookup_expr="lte")
    year__gt = django_filters.NumberFilter(field_name="year", lookup_expr="gt")
    year__lt = django_filters.NumberFilter(field_name="year", lookup_expr="lt")

    # duplicated here - for the html front end filters:
    first_year = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    last_year = django_filters.NumberFilter(field_name="year", lookup_expr="lte")

    prj_date0 = django_filters.DateFilter(
        field_name="prj_date0", help_text="format: yyyy-mm-dd"
    )
    prj_date0__gte = django_filters.DateFilter(
        field_name="prj_date0", lookup_expr="gte", help_text="format: yyyy-mm-dd"
    )
    prj_date0__lte = django_filters.DateFilter(
        field_name="prj_date0", lookup_expr="lte", help_text="format: yyyy-mm-dd"
    )

    prj_date1 = django_filters.DateFilter(
        field_name="prj_date1", help_text="format: yyyy-mm-dd"
    )
    prj_date1__gte = django_filters.DateFilter(
        field_name="prj_date1", lookup_expr="gte", help_text="format: yyyy-mm-dd"
    )
    prj_date1__lte = django_filters.DateFilter(
        field_name="prj_date1", lookup_expr="lte", help_text="format: yyyy-mm-dd"
    )

    protocol = ValueInFilter(field_name="protocol__abbrev")
    protocol__not = ValueInFilter(field_name="protocol__abbrev", exclude=True)

    prj_cd = ValueInFilter(field_name="prj_cd")
    prj_cd__not = ValueInFilter(field_name="prj_cd", exclude=True)

    prj_cd__like = django_filters.CharFilter(
        field_name="prj_cd", lookup_expr="icontains"
    )
    prj_cd__not_like = django_filters.CharFilter(
        field_name="prj_cd", lookup_expr="icontains", exclude=True
    )

    prj_cd__endswith = django_filters.CharFilter(
        field_name="prj_cd", lookup_expr="endswith"
    )
    prj_cd__not_endswith = django_filters.CharFilter(
        field_name="prj_cd", lookup_expr="endswith", exclude=True
    )

    prj_nm__like = django_filters.CharFilter(
        field_name="prj_nm", lookup_expr="icontains"
    )

    prj_nm__not_like = django_filters.CharFilter(
        field_name="prj_nm", lookup_expr="icontains", exclude=True
    )

    prj_ldr = django_filters.CharFilter(
        field_name="prj_ldr__username", lookup_expr="iexact"
    )

    lake = ValueInFilter(field_name="lake__abbrev")
    lake__not = ValueInFilter(field_name="lake__abbrev", exclude=True)

    # scope protocol, project_type

    class Meta:
        model = Project
        # fields = ['year', 'project_type', 'lake', 'funding']
        fields = ["year", "project_type", "lake__abbrev", "protocol", "prj_cd"]


#    def __init__(self, *args, **kwargs):
#        # from https://github.com/alex/django-filter/issues/29
#        super(ProjectFilter, self).__init__(*args, **kwargs)
#        filter_ = self.filters["project_type"]
#
#        # this will grab all the fk ids that are in use
#        fk_counts = (
#            Project.objects.values_list("project_type")
#            .order_by("project_type")
#            .annotate(models.Count("project_type"))
#        )
#        ProjectType_ids = [fk for fk, cnt in fk_counts]
#        filter_.extra["queryset"] = ProjectType.objects.filter(pk__in=ProjectType_ids)
#
#    @property
#    def form(self):
#        self._form = super(ProjectFilter, self).form
#        self._form.helper = FormHelper()
#        self._form.helper.form_style = "inline"
#        self._form.helper.form_method = "get"
#        self._form.helper.form_action = ""
#
#        self._form.fields.update(
#            {
#                "year": forms.ChoiceField(
#                    label="Year:", choices=get_year_choices(), required=False
#                )
#            }
#        )
#
#        self._form.fields.update(
#            {
#                "lake": forms.ModelChoiceField(
#                    label="Lake:", queryset=Lake.objects.all(), required=False
#                )
#            }
#        )
#
#        self._form.fields.update(
#            {
#                "project_type": forms.ModelChoiceField(
#                    label="Project Type:",
#                    queryset=ProjectType.objects.all().order_by("project_type"),
#                    required=False,
#                )
#            }
#        )
#
#        self._form.helper.add_input(Submit("submit", "Apply Filter"))
#        self._form.helper.layout = Layout(
#            Field("year"),
#            Field("project_type"),
#            Field("lake"),
#            # Field('funding'),
#        )
#
#        return self._form
#


class SamplePointFilter(GeoFilterSet):
    """A filter for sample points lists"""

    within__roi = GeomFilter(
        field_name="geom__within",
        method="filter_roi",
    )
    intersects__roi = GeomFilter(
        field_name="geom__intersects",
        method="filter_roi",
    )

    within__buffered_point = GeomFilter(
        field_name="project__multipoints__geom__within",
        method="filter_point",
    )
    intersects__buffered_point = GeomFilter(
        field_name="geom__intersects",
        method="filter_point",
    )

    project_type = django_filters.ModelMultipleChoiceFilter(
        "project__project_type",
        to_field_name="id",
        lookup_expr="in",
        queryset=ProjectType.objects.all(),
    )

    year = django_filters.CharFilter(field_name="project__year", lookup_expr="exact")
    year__gte = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="gte"
    )
    year__lte = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="lte"
    )
    year__gt = django_filters.NumberFilter(field_name="project__year", lookup_expr="gt")
    year__lt = django_filters.NumberFilter(field_name="project__year", lookup_expr="lt")

    # duplicated here - for the html front end filters:
    first_year = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="gte"
    )
    last_year = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="lte"
    )

    prj_date0 = django_filters.DateFilter(
        field_name="project__prj_date0", help_text="format: yyyy-mm-dd"
    )
    prj_date0__gte = django_filters.DateFilter(
        field_name="project__prj_date0",
        lookup_expr="gte",
        help_text="format: yyyy-mm-dd",
    )
    prj_date0__lte = django_filters.DateFilter(
        field_name="project__prj_date0",
        lookup_expr="lte",
        help_text="format: yyyy-mm-dd",
    )

    prj_date1 = django_filters.DateFilter(
        field_name="project__prj_date1", help_text="format: yyyy-mm-dd"
    )
    prj_date1__gte = django_filters.DateFilter(
        field_name="project__prj_date1",
        lookup_expr="gte",
        help_text="format: yyyy-mm-dd",
    )
    prj_date1__lte = django_filters.DateFilter(
        field_name="project__prj_date1",
        lookup_expr="lte",
        help_text="format: yyyy-mm-dd",
    )

    protocol = ValueInFilter(field_name="project__protocol__abbrev")
    protocol__not = ValueInFilter(field_name="project__protocol__abbrev", exclude=True)

    prj_cd = ValueInFilter(field_name="project__prj_cd")
    prj_cd__not = ValueInFilter(field_name="project__prj_cd", exclude=True)

    prj_cd__like = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="icontains"
    )
    prj_cd__not_like = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="icontains", exclude=True
    )

    prj_cd__endswith = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="endswith"
    )
    prj_cd__not_endswith = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="endswith", exclude=True
    )

    prj_nm__like = django_filters.CharFilter(
        field_name="project__prj_nm", lookup_expr="icontains"
    )

    prj_nm__not_like = django_filters.CharFilter(
        field_name="project__prj_nm", lookup_expr="icontains", exclude=True
    )

    prj_ldr = django_filters.CharFilter(
        field_name="project__prj_ldr__username", lookup_expr="iexact"
    )

    lake = ValueInFilter(field_name="project__lake__abbrev")
    lake__not = ValueInFilter(field_name="project__lake__abbrev", exclude=True)

    class Meta:
        model = SamplePoint
        fields = ["project__year", "project__project_type", "project__lake__abbrev"]


class ReportFilter(GeoFilterSet):
    """A filter for our ReportFiles"""

    within__roi = GeomFilter(
        field_name="projectreport__project__multipoints__geom__within",
        method="filter_roi",
    )
    intersects__roi = GeomFilter(
        field_name="projectreport__project__multipoints__geom__intersects",
        method="filter_roi",
    )

    within__buffered_point = GeomFilter(
        field_name="projectreport__project__multipoints__geom__within",
        method="filter_point",
    )
    intersects__buffered_point = GeomFilter(
        field_name="projectreport__project__multipoints__geom__intersects",
        method="filter_point",
    )

    report_type = ValueInFilter(field_name="projectreport__milestone__label_abbrev")
    report_type__not = ValueInFilter(
        field_name="projectreport__milestone__label_abbrev", exclude=True
    )

    project_type = ValueInFilter(
        field_name="projectreport__project__project_type__id", lookup_expr="in"
    )
    scope = ValueInFilter(
        field_name="projectreport__project__project_type__scope", lookup_expr="in"
    )

    year = django_filters.CharFilter(
        field_name="projectreport__project__year", lookup_expr="exact"
    )
    year__gte = django_filters.NumberFilter(
        field_name="projectreport__project__year", lookup_expr="gte"
    )
    year__lte = django_filters.NumberFilter(
        field_name="projectreport__project__year", lookup_expr="lte"
    )
    year__gt = django_filters.NumberFilter(
        field_name="projectreport__project__year", lookup_expr="gt"
    )
    year__lt = django_filters.NumberFilter(
        field_name="projectreport__project__year", lookup_expr="lt"
    )

    # duplicated here - for the html front end filters:
    first_year = django_filters.NumberFilter(
        field_name="projectreport__project__year", lookup_expr="gte"
    )
    last_year = django_filters.NumberFilter(
        field_name="projectreport__project__year", lookup_expr="lte"
    )

    prj_date0 = django_filters.DateFilter(
        field_name="projectreport__project__prj_date0", help_text="format: yyyy-mm-dd"
    )
    prj_date0__gte = django_filters.DateFilter(
        field_name="projectreport__project__prj_date0",
        lookup_expr="gte",
        help_text="format: yyyy-mm-dd",
    )
    prj_date0__lte = django_filters.DateFilter(
        field_name="projectreport__project__prj_date0",
        lookup_expr="lte",
        help_text="format: yyyy-mm-dd",
    )

    prj_date1 = django_filters.DateFilter(
        field_name="projectreport__project__prj_date1", help_text="format: yyyy-mm-dd"
    )
    prj_date1__gte = django_filters.DateFilter(
        field_name="projectreport__project__prj_date1",
        lookup_expr="gte",
        help_text="format: yyyy-mm-dd",
    )
    prj_date1__lte = django_filters.DateFilter(
        field_name="projectreport__project__prj_date1",
        lookup_expr="lte",
        help_text="format: yyyy-mm-dd",
    )

    protocol = ValueInFilter(field_name="projectreport__project__protocol__abbrev")
    protocol__not = ValueInFilter(
        field_name="projectreport__project__protocol__abbrev", exclude=True
    )

    prj_cd = ValueInFilter(field_name="projectreport__project__prj_cd")
    prj_cd__not = ValueInFilter(
        field_name="projectreport__project__prj_cd", exclude=True
    )

    prj_cd__like = django_filters.CharFilter(
        field_name="projectreport__project__prj_cd", lookup_expr="icontains"
    )
    prj_cd__not_like = django_filters.CharFilter(
        field_name="projectreport__project__prj_cd",
        lookup_expr="icontains",
        exclude=True,
    )

    prj_cd__endswith = django_filters.CharFilter(
        field_name="projectreport__project__prj_cd", lookup_expr="endswith"
    )
    prj_cd__not_endswith = django_filters.CharFilter(
        field_name="projectreport__project__prj_cd",
        lookup_expr="endswith",
        exclude=True,
    )

    prj_nm__like = django_filters.CharFilter(
        field_name="projectreport__project__prj_nm", lookup_expr="icontains"
    )

    prj_nm__not_like = django_filters.CharFilter(
        field_name="projectreport__project__prj_nm",
        lookup_expr="icontains",
        exclude=True,
    )

    prj_ldr = django_filters.CharFilter(
        field_name="projectreport__project__prj_ldr__username", lookup_expr="iexact"
    )

    lake = ValueInFilter(field_name="projectreport__project__lake__abbrev")
    lake__not = ValueInFilter(
        field_name="projectreport__project__lake__abbrev", exclude=True
    )

    class Meta:
        model = Report
        fields = [
            "current",
            "uploaded_on",
        ]


class AssociatedFileFilter(GeoFilterSet):
    """A filter for our AssociatedFiles"""

    within__roi = GeomFilter(
        field_name="project__multipoints__geom__within",
        method="filter_roi",
    )
    intersects__roi = GeomFilter(
        field_name="project__multipoints__geom__intersects",
        method="filter_roi",
    )

    within__buffered_point = GeomFilter(
        field_name="project__multipoints__geom__within",
        method="filter_point",
    )
    intersects__buffered_point = GeomFilter(
        field_name="project__multipoints__geom__intersects",
        method="filter_point",
    )

    project_type = ValueInFilter(
        field_name="project__project_type__id", lookup_expr="in"
    )
    scope = ValueInFilter(field_name="project__project_type__scope", lookup_expr="in")

    year = django_filters.CharFilter(field_name="project__year", lookup_expr="exact")
    year__gte = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="gte"
    )
    year__lte = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="lte"
    )
    year__gt = django_filters.NumberFilter(field_name="project__year", lookup_expr="gt")
    year__lt = django_filters.NumberFilter(field_name="project__year", lookup_expr="lt")

    # duplicated here - for the html front end filters:
    first_year = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="gte"
    )
    last_year = django_filters.NumberFilter(
        field_name="project__year", lookup_expr="lte"
    )

    prj_date0 = django_filters.DateFilter(
        field_name="project__prj_date0", help_text="format: yyyy-mm-dd"
    )
    prj_date0__gte = django_filters.DateFilter(
        field_name="project__prj_date0",
        lookup_expr="gte",
        help_text="format: yyyy-mm-dd",
    )
    prj_date0__lte = django_filters.DateFilter(
        field_name="project__prj_date0",
        lookup_expr="lte",
        help_text="format: yyyy-mm-dd",
    )

    prj_date1 = django_filters.DateFilter(
        field_name="project__prj_date1", help_text="format: yyyy-mm-dd"
    )
    prj_date1__gte = django_filters.DateFilter(
        field_name="project__prj_date1",
        lookup_expr="gte",
        help_text="format: yyyy-mm-dd",
    )
    prj_date1__lte = django_filters.DateFilter(
        field_name="project__prj_date1",
        lookup_expr="lte",
        help_text="format: yyyy-mm-dd",
    )

    protocol = ValueInFilter(field_name="project__protocol__abbrev")
    protocol__not = ValueInFilter(field_name="project__protocol__abbrev", exclude=True)

    prj_cd = ValueInFilter(field_name="project__prj_cd")
    prj_cd__not = ValueInFilter(field_name="project__prj_cd", exclude=True)

    prj_cd__like = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="icontains"
    )
    prj_cd__not_like = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="icontains", exclude=True
    )

    prj_cd__endswith = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="endswith"
    )
    prj_cd__not_endswith = django_filters.CharFilter(
        field_name="project__prj_cd", lookup_expr="endswith", exclude=True
    )

    prj_nm__like = django_filters.CharFilter(
        field_name="project__prj_nm", lookup_expr="icontains"
    )

    prj_nm__not_like = django_filters.CharFilter(
        field_name="project__prj_nm", lookup_expr="icontains", exclude=True
    )

    prj_ldr = django_filters.CharFilter(
        field_name="project__prj_ldr__username", lookup_expr="iexact"
    )

    lake = ValueInFilter(field_name="project__lake__abbrev")
    lake__not = ValueInFilter(field_name="project__lake__abbrev", exclude=True)

    class Meta:
        model = AssociatedFile
        fields = [
            "current",
            "uploaded_on",
        ]
