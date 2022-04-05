"""=============================================================
 c:/Users/COTTRILLAD/1work/Python/djcode/apps/pjtk2/pjtk2/tests/integration_tests/test_spatial_pts_upload.py
 Created: 05 Feb 2021 09:11:50

 DESCRIPTION:

  The tests in this file verify that the interface that allows users
  to upload spatial data works as expected:

  + only available to staff who can edit the project (owner, admin, or
  manager)

  + acceps csv or xlxs

  + append or replace

  + throws an error if the uploaded file does not have a header with
    the appopriate names

  + captures malformed points or those outside of GL Basin (for now)

  + point label is required

  + includes helpful instructions describing what spatial data is
  relevant (creels vs field project vs synthesis)

  + upload format should match format returned by api endpoint - will
  allow us to download, edit and then re-upload points.

  + consider adding download to xlsx button on each project page if
  spatial data exists.

 A. Cottrill
=============================================================

"""

import csv
import pytest

from django.utils.html import escape
from django.urls import reverse
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import StringIO, BytesIO
from openpyxl import Workbook
from pytest_django.asserts import assertTemplateUsed, assertContains

from pjtk2.tests.pytest_fixtures import user, joe_user, dba, manager


from pjtk2.models import ProjectPolygon

from ..factories import (
    LakeFactory,
    ProjectFactory,
    MilestoneFactory,
    SamplePointFactory,
)


def csv_file_upload(data):
    """Given a list of data, return a stringIO object that emulates a csv file.

    Arguments:
    - `data`: - a list of lists to be included in our csv_file.
    """

    stringio = StringIO()

    csv.writer(stringio).writerows(data)
    points_file = InMemoryUploadedFile(
        stringio, None, "foo.csv", "text", stringio.tell(), None
    )
    points_file.seek(0)
    return points_file


def xlsx_file_upload(data):
    """given a list of data, return an openpyxl workbook as BytesIO object
    that can emulate data uploaded in a spreadsheet.

    Arguments:
    - `data`:

    """
    virtual_workbook = BytesIO()
    wb = Workbook()
    sheet = wb.active
    for row in data:
        sheet.append(row)
    wb.save(virtual_workbook)
    points_file = InMemoryUploadedFile(
        virtual_workbook, None, "foo.xlsx", "text", virtual_workbook.tell(), None
    )
    points_file.seek(0)
    return points_file


@pytest.fixture
def lake():
    """"""
    # a simple retangular polygon to represent the geometry
    # associated with lake.  All of our uploaded points will have
    # to fall within this polygon.
    geom = (
        "MULTIPOLYGON(((-83.00 44.00,"
        + "-84.0 44.00,"
        + "-84.00 45.00,"
        + "-83.00 45.00,"
        + "-83.00 44.00)))"
    )
    lake = LakeFactory(
        lake_name="Lake Huron",
        abbrev="HU",
        geom=GEOSGeometry(geom.replace("\n", ""), srid=4326),
    )

    return lake


@pytest.fixture
def project(user, lake):
    """

    Arguments:
    - `project`:
    """

    MilestoneFactory.create(label="Approved")
    MilestoneFactory.create(label="Sign Off")

    project = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=user, lake=lake)

    # add four sample points that create a polygon to our project
    SamplePointFactory(
        project=project,
        label="A",
        geom=GEOSGeometry("POINT(-83.04 44.04)"),
    )

    SamplePointFactory(
        project=project,
        label="B",
        geom=GEOSGeometry("POINT(-83.44 44.44)"),
    )

    SamplePointFactory(
        project=project,
        label="C",
        geom=GEOSGeometry("POINT(-83.74 44.04)"),
    )

    SamplePointFactory(
        project=project,
        label="D",
        geom=GEOSGeometry("POINT(-83.74 44.44)"),
    )

    project.update_convex_hull()

    return project


@pytest.fixture
def pts():
    """make sure all of our points are within our lake's geometry"""
    pts = [
        ["POINT_LABEL", "DD_LAT", "DD_LON"],
        ["1", "44.608", "-83.580"],
        ["10", "44.718", "-83.636"],
        ["11", "44.692", "-83.629"],
    ]
    return pts


@pytest.mark.django_db
def test_upload_spatial_points_button_on_detail_page(
    client, user, joe_user, manager, dba, project
):
    """The button to upload spatial data should be available to
    authenticated users on the project detail page."""

    users = [
        # (None, False),
        (joe_user, False),
        (user, True),
        (manager, True),
        (dba, True),
    ]
    url = reverse("project_detail", kwargs={"slug": project.slug})
    upload_url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    for item in users:
        login = client.login(username=item[0].username, password="Abcd1234")
        assert login is True
        response = client.get(url, follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert (upload_url in content) is item[1]
        assert ("Upload Spatial Points" in content) is item[1]


@pytest.mark.django_db
def test_point_upload_can_edit(client, user, joe_user, manager, dba, project):
    """The form should not be accessible to users who cannot edit the
    project.  Users who cannot edit the page, should be redirected to
    the proejct detail if they try to access the url.

    """
    # a list of our users and whether or not they can upload points:
    users = [
        (joe_user, False),
        (user, True),
        (manager, True),
        (dba, True),
    ]
    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    for item in users:
        login = client.login(username=item[0].username, password="Abcd1234")
        assert login is True
        response = client.get(url, follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        can_edit = item[1]

        if can_edit:
            assert "<h2>Upload Spatial Points</h2>" in content
            assert "<strong>Spatial Data Upload</strong>" in content
            assert "pjtk2/UploadSpatialPoints.html" in [
                t.name for t in response.templates
            ]
        else:
            # users who can't edit our project are redirected back to the detail page:
            assert "Project Details" in content
            assert "pjtk2/projectdetail.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_point_upload_anonymous(client, project):
    """If an anonymous user attemps to access the view to upload spatial
    points, they should be re-directed to the login page.

    """

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})
    response = client.get(url, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "Project Tracker Login" in content
    assert "registration/login.html" in [t.name for t in response.templates]


def test_upload_page_contains_detailed_instructions(client, user, project):
    """The upload page should contain detailed instructions about what
    spatial should be included (how it is different for randomized field
    projects, fixed site proejcts, and synthesis/integrated analsysis
    project) It should also indicate the criteria, and include an sample
    table with a small number of examples.

    Arguments:
    - `client`:
    - `user`:
    - `project`:

    """

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})
    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.get(url, follow=True)
    assert response.status_code == 200
    # content = response.content.decode("utf-8")

    elements = [
        "<strong>Coordinates of Each Sample</strong>",
        "<strong>Fixed Sites</strong>",
        "<strong>Grid Centroids</strong>",
        "<strong>Synthesis/Integrated Analysis</strong>",
    ]

    for element in elements:
        assertContains(response, element, html=True)

    elements = [
        "spatial-validation-rules",
        "example-spatial-data",
    ]
    for element in elements:
        assertContains(response, element, html=False)


def test_point_bad_header(client, project, user, pts):
    """If the uploaded file does not have the correcting headings in the
    first row, return an appropriate error message.

    """

    # remove the header:
    pts.pop(0)

    points_file = xlsx_file_upload(pts)
    form_data = {"replace": "replace", "points_file": points_file}
    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    msg = "Malformed header in submitted file."
    assert msg in content


def test_point_bad_latlong(client, project, user, pts):
    """IF the coordinates are cannot be converted to points, an
    appropriate error should be returned.

    """

    # replace one of the latitude values with a value that cannot be
    # converted to a float:
    pts[1][1] = "FOO"

    points_file = xlsx_file_upload(pts)
    form_data = {"replace": "replace", "points_file": points_file}
    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    msg = "At least one point has an invalid latitude or longitude."
    assert msg in content


@pytest.mark.django_db
def test_point_out_of_bounds(client, user, project, pts):
    """If one or more of the points in the uploaded file are outside the
    bounds of the lake associated with the project, then return an
    appropriate error message.  For now, we will use the bounding box
    for the lake, but it could be more refined in the future.

    """

    # update the latitude of one points to be south of our lake.
    pts[1][1] = "41.00"

    points_file = csv_file_upload(pts)
    form_data = {"replace": "replace", "points_file": points_file}
    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    #
    messages = [
        "1 of the supplied points are not within the bounds of the lake",
        "associated with this project.",
    ]
    for msg in messages:
        assert msg in content


def test_points_missing_label(client, project, user, pts):
    """Every point must have label - it labels are missing or empty
    strings, raise an error.

    """

    # replace one of the labels with a blank string:
    pts[1][0] = ""

    points_file = xlsx_file_upload(pts)
    form_data = {"replace": "replace", "points_file": points_file}
    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    msg = "At least one point is missing a label"
    assert msg in content


def test_spatial_pts_upload_other_file_types(client, user, project):
    """The form should not accept any other file type."""

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    points_file = BytesIO(b"mybinarydata")
    points_file.name = "myimage.jpg"

    form_data = {"replace": "replace", "points_file": points_file}
    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")
    # msg = 'File extension ".jpg" is not allowed. Allowed extensions are: csv, xlsx.'
    # quotes in full message cause test to fail now.
    msg = "is not allowed. Allowed extensions are: csv, xlsx."
    assert msg in content


def test_accepts_append_or_replace_is_required(client, user, project, pts):
    """At least one of the radio buttons needs to be selected. If the data
    is submitted without specifying whether or not the points should be
    appended to existing points or replace them altogether, the form
    should be invalid and an appropriate error message included in the
    response.

    """

    points_file = csv_file_upload(pts)

    form_data = {"points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert "This field is required" in content


def test_append_xlsx(client, user, project, pts):
    """if the append option is specified when the data is submitted as an
    xlsx file, the points should be added to ones already present."""

    # get the labels of points associated with our project before
    prior_labels = [x[0] for x in project.get_sample_points()]

    points_file = xlsx_file_upload(pts)
    # don't forget to account for the header:
    points_labels = [x[0] for x in pts[1:]]

    form_data = {"replace": "append", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200

    observed_labels = [x[0] for x in project.get_sample_points()]
    expected_labels = points_labels + prior_labels
    # our expected labels should be the original ones plus the new
    # ones we passed in:
    assert set(expected_labels) == set(observed_labels)


def test_replace_xlsx(client, project, user, pts):
    """if the replace option is specified when the data is submitted as an
    xlsx file, the points should replace any that are already present."""

    # get the number of points associated with our project before
    points_prior = len(project.get_sample_points())

    points_file = xlsx_file_upload(pts)

    form_data = {"replace": "replace", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200

    points_after = project.get_sample_points()
    assert points_prior != len(points_after)

    expected_labels = [x[0] for x in pts[1:]]
    observed_labels = [x[0] for x in points_after]
    assert set(expected_labels) == set(observed_labels)


@pytest.mark.django_db
def test_append_quoted_csv(client, project, user, pts):
    """There were issues with the csv upload depending on how the csv was
    built.  Some application wrap values with quotes, some don't.  Values
    with quote were causeing errors when they should have been fine.

    """

    # get the labels of points associated with our project before
    prior_labels = [x[0] for x in project.get_sample_points()]

    # wrap all of the values in our list in quotes before passing it
    # to csv file upload
    for i, item in enumerate(pts):
        pts[i] = ['"{}"'.format(x) for x in item]

    points_file = csv_file_upload(pts)
    points_labels = [x[0].replace('"', "") for x in pts[1:]]

    form_data = {"replace": "append", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200

    observed_labels = [x[0] for x in project.get_sample_points()]
    expected_labels = points_labels + prior_labels
    # our expected labels should be the original ones plus the new
    # ones we passed in:
    assert set(expected_labels) == set(observed_labels)


@pytest.mark.django_db
def test_append_csv(client, project, user, pts):
    """if the append option is specified when the data is submitted as an
    csv file, the points should be added to ones already present."""

    # get the labels of points associated with our project before
    prior_labels = [x[0] for x in project.get_sample_points()]

    points_file = csv_file_upload(pts)
    points_labels = [x[0] for x in pts[1:]]

    form_data = {"replace": "append", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200

    observed_labels = [x[0] for x in project.get_sample_points()]
    expected_labels = points_labels + prior_labels
    # our expected labels should be the original ones plus the new
    # ones we passed in:
    assert set(expected_labels) == set(observed_labels)


@pytest.mark.django_db
def test_replace_csv(client, project, user, pts):
    """if the replace option is specified when the data is submitted as an
    csv file, the points should replace any that are already present."""

    # get the number of points associated with our project before
    points_prior = len(project.get_sample_points())

    points_file = csv_file_upload(pts)

    form_data = {"replace": "replace", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200

    points_after = project.get_sample_points()
    assert points_prior != len(points_after)

    expected_labels = [x[0] for x in pts[1:]]
    observed_labels = [x[0] for x in points_after]
    assert set(expected_labels) == set(observed_labels)


def test_project_polygon_updated(client, project, user, pts):
    """Verify that the project polygon for our proejct is updated after we
    submit new points.

    """

    geom_prior = ProjectPolygon.objects.get(project=project).geom

    points_file = csv_file_upload(pts)
    points_labels = [x[0] for x in pts[1:]]

    form_data = {"replace": "append", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200

    geom_after = ProjectPolygon.objects.get(project=project).geom

    # our expected labels should be the original ones plus the new
    # ones we passed in:
    assert geom_after != geom_prior


def test_project_maximum_upload_size(client, project, user, pts):
    """We should have a limit on the number of rows/points that can be
    uploaded at one time.  If the user tries to upload more than that, a
    warning should be returned to the user.

    """
    # grab the points without the header and add a bunch of copies
    pts.extend(pts[1:] * 500)
    points_file = csv_file_upload(pts)

    form_data = {"replace": "replace", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    MAX_UPLOAD_POINTS = 1000
    msg = (
        "The points file contains more than {} points! ".format(MAX_UPLOAD_POINTS)
        + "Reduce the number of points and try again."
    )

    assert msg in content


def test_upload_no_data(client, project, user, pts):
    """We should have a limit on the number of rows/points that can be
    uploaded at one time.  If the user tries to upload more than that, a
    warning should be returned to the user.

    """
    # grab the points without the header and add a bunch of copies
    header = pts.pop(0)
    print("header={}".format(header))
    points_file = csv_file_upload(
        [
            header,
        ]
    )

    form_data = {"replace": "replace", "points_file": points_file}

    url = reverse("spatial_point_upload", kwargs={"slug": project.slug})

    login = client.login(username=user.username, password="Abcd1234")
    assert login is True
    response = client.post(url, form_data, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    msg = "Points_File does not appear to contain any data!"
    assert msg in content
