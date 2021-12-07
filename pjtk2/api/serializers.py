from rest_framework import serializers
from django.contrib.auth import get_user_model
from pjtk2.models import (
    Project,
    ProjectType,
    SamplePoint,
    ProjectPolygon,
    ProjectImage,
    Report,
)

User = get_user_model()


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        lookup_field = "username"
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_staff",
            "is_active",
        )
        ordering = ["id"]


class ProjectTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProjectType
        fields = ("project_type", "field_component")
        ordering = ["id"]


class ProjectSerializer(serializers.HyperlinkedModelSerializer):

    sample_points = serializers.HyperlinkedIdentityField(
        view_name="api:project_points", lookup_field="slug"
    )

    prj_ldr = UserSerializer()

    project_type = serializers.CharField(
        source="project_type.project_type", read_only=True
    )

    class Meta:
        model = Project
        lookup_field = "slug"
        fields = (
            "year",
            "prj_cd",
            "slug",
            "prj_nm",
            "prj_date0",
            "prj_date1",
            "project_type",
            "prj_ldr",
            "comment",
            "sample_points",
        )


class ProjectImageSerializer(serializers.ModelSerializer):
    """A serializer that returns attributes of images - uses as a
    nested component of the project abstract serializer."""

    class Meta:
        model = ProjectImage
        fields = (
            "order",
            "image_path",
            "caption",
            # "aria-text",
            "report",
        )


class ReportSerializer(serializers.ModelSerializer):
    """serialize our report objects so they can be downloaded by client
    applications."""

    prj_cd = serializers.CharField(read_only=True)
    prj_nm = serializers.CharField(read_only=True)
    report_type = serializers.CharField(read_only=True)
    report_path = serializers.CharField(read_only=True)
    uploaded_by = serializers.CharField(read_only=True, source="_uploaded_by")

    class Meta:
        model = Report
        fields = (
            "prj_cd",
            "prj_nm",
            "report_type",
            "current",
            "report_path",
            "uploaded_on",
            "uploaded_by",
        )


class AssociatedFileSerializer(serializers.ModelSerializer):
    """serialize our associated objects so they can be downloaded by client
    applications."""

    prj_cd = serializers.CharField(read_only=True)
    prj_nm = serializers.CharField(read_only=True)
    file_path = serializers.CharField(read_only=True)
    uploaded_by = serializers.CharField(read_only=True, source="_uploaded_by")

    class Meta:
        model = Report
        fields = (
            "prj_cd",
            "prj_nm",
            "current",
            "file_path",
            "uploaded_on",
            "uploaded_by",
        )


class ProjectAbstractSerializer(serializers.HyperlinkedModelSerializer):
    """An api endpoint that returns project elements required to generate
    the annual assessment reports, including any assoicatiated images.

    TODO: ADD IMAGES

    """

    project_leader = serializers.SerializerMethodField()
    images = ProjectImageSerializer(many=True)
    project_type = serializers.CharField(
        source="project_type.project_type", read_only=True
    )

    class Meta:
        model = Project
        lookup_field = "slug"
        fields = (
            "year",
            "prj_cd",
            "slug",
            "prj_nm",
            "prj_date0",
            "prj_date1",
            "project_type",
            "project_leader",
            "abstract",
            "images",
        )

    def get_project_leader(self, obj):
        """return the project lead as a concatenated string that includes the
        first name and last name."""
        return "{} {}".format(obj.prj_ldr.first_name, obj.prj_ldr.last_name)


class ProjectPointSerializer(serializers.ModelSerializer):

    prj_cd = serializers.CharField(source="project.prj_cd", read_only=True)
    project_type = serializers.CharField(source="project.project_type", read_only=True)

    class Meta:
        model = SamplePoint
        fields = (
            "prj_cd",
            "label",
            "dd_lat",
            "dd_lon",
            "popup_text",
            "project_type",
        )


class ProjectPolygonSerializer(serializers.HyperlinkedModelSerializer):

    prj_cd = serializers.CharField(source="project.prj_cd", read_only=True)

    class Meta:
        model = ProjectPolygon
        fields = ("prj_cd", "geom")
