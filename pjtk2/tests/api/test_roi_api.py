import pytest
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Q
from django.test import RequestFactory
from django.urls import reverse
from pjtk2.api.serializers import ProjectPointSerializer
from pjtk2.models import SamplePoint
from pjtk2.tests.factories import ProjectFactory, SamplePointFactory
from rest_framework import status
from rest_framework.test import APITestCase


class ProjectAPITest(APITestCase):
    def setUp(self):

        self.factory = RequestFactory()

        grid = (
            "MULTIPOLYGON(((-82.000000033378 43.9999999705306,"
            + "-82.0833359084557 43.9999999705305,"
            + "-82.0833359084557 44.0833320331081,"
            + "-82.000000033378 44.0833320331082,"
            + "-82.000000033378 43.9999999705306)))"
        )
        self.roi = GEOSGeometry(grid.replace("\n", ""), srid=4326)

        grid = (
            "MULTIPOLYGON(((-83.000000033378 43.9999999705306,"
            + "-83.0833359084557 43.9999999705305,"
            + "-83.0833359084557 44.0833320331081,"
            + "-83.000000033378 44.0833320331082,"
            + "-83.000000033378 43.9999999705306)))"
        )
        self.roi2 = GEOSGeometry(grid.replace("\n", ""), srid=4326)

        self.line = GEOSGeometry("LINESTRING(-83.08 43.99, -83.08 44.08)", srid=4326)

        # we need to create some models with different years - starting
        # with the current year.

        prj_cd = "LHA_IA16_INN"
        self.project1 = ProjectFactory(prj_cd=prj_cd, prj_nm="All In Roi")

        # these are four randomly selected points that all fall within the roi
        pts = [
            "POINT(-82.081126628131 44.000970817096)",
            "POINT(-82.0456637754061 44.0649121962459)",
            "POINT(-82.024922507764 44.0171801372301)",
            "POINT(-82.0017671634393 44.0513359855003)",
        ]
        for i, pt in enumerate(pts):
            SamplePointFactory(
                project=self.project1, label="In-{}".format(i), geom=GEOSGeometry(pt)
            )

        self.project1.update_multipoints()

        prj_cd = "LHA_IA16_LAP"
        self.project2 = ProjectFactory(prj_cd=prj_cd, prj_nm="Some In Roi")

        # the first two points are in the roi, the last two are not:
        pts = [
            "POINT(-82.081126628131 44.000970817096)",
            "POINT(-82.0456637754061 44.0649121962459)",
            "POINT(-82.1249999941107 44.0416640136496)",
            "POINT(-81.9583320623296 44.0416640159647)",
        ]

        for i, pt in enumerate(pts):
            SamplePointFactory(
                project=self.project2, label="some-{}".format(i), geom=GEOSGeometry(pt)
            )

        self.project2.update_multipoints()

        # a project with all of its points outside our region of interest
        prj_cd = "LHA_IA16_OUT"
        self.project3 = ProjectFactory(prj_cd=prj_cd, prj_nm="NOT In Roi")

        # these are four points north, south, east and west of the roi
        pts = [
            "POINT(-82.0416679351682 43.9583319806175)",
            "POINT(-82.0416679337938 44.1249979556483)",
            "POINT(-82.1249999941107 44.0416640136496)",
            "POINT(-81.9583320623296 44.0416640159647)",
        ]

        for i, pt in enumerate(pts):
            SamplePointFactory(
                project=self.project3, label="out-{}".format(i), geom=GEOSGeometry(pt)
            )

        self.project3.update_multipoints()

        prj_cd = "LHA_IA16_000"
        self.project4 = ProjectFactory(prj_cd=prj_cd, prj_nm="No Points")

    def test_points_in_roi_api_get_put_delete(self):
        """the points api is currently readonly, but requires a post request
        (which holds the roi). Any other request type should throw an
        error.

        """

        url = reverse("api:get_points_in_roi")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_points_in_roi_api_post_good_roi_wkt(self):
        """If we pass in a valid roi as wkt, the api should return a list of
        sample points contained in the roi.  It will not include points
        outside of the roi.

        """

        url = reverse("api:get_points_in_roi")
        data = {"roi": self.roi.wkt}
        response = self.client.post(url, data)
        request = self.factory.get(url)

        # get data from db using the same sort - order
        slug = self.project1.slug
        points = SamplePoint.objects.filter(
            Q(project__slug=slug) | Q(label__in=["some-0", "some-1"])
        ).order_by("-project__year", "label")
        serializer = ProjectPointSerializer(
            points, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(serializer.data))
        self.assertEqual(response.data, serializer.data)

    def test_points_in_roi_api_post_good_roi_json(self):
        """If we pass in a valid roi as json, the api should return a
        list of sample points contained in the roi.  It will not
        include points outside of the roi.
        """

        slug = self.project1.slug
        data = {"roi": self.roi.geojson}

        url = reverse("api:get_points_in_roi")
        response = self.client.post(url, data)

        # get data from db using the same sort - order
        points = SamplePoint.objects.filter(
            Q(project__slug=slug) | Q(label__in=["some-0", "some-1"])
        ).order_by("-project__year", "label")

        request = self.factory.get(url)
        serializer = ProjectPointSerializer(
            points, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_points_in_roi_api_post_no_points(self):
        """If we pass in a valid roi, that does not include any sample points,
        the api shouldn't return any data, but should not fail or
        issue a warning.

        """

        url = reverse("api:get_points_in_roi")
        data = {"roi": self.roi2.wkt}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_points_in_roi_api_post_bad_roi_line(self):
        """If the roi in the post request does not form a valid polygon, an
        appropriate error should be thrown.

        """
        url = reverse("api:get_points_in_roi")
        data = {"roi": self.line.wkt}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi is not a valid polygon."
        self.assertIn(errmsg, str(response.content))

    def test_points_in_roi_api_post_bad_roi_point(self):
        """If the roi in the post request does not form a valid polygon, an
        appropriate error should be thrown.

        """

        url = reverse("api:get_points_in_roi")
        data = {"roi": "POINT(-82.024922507764 44.0171801372301)"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi is not a valid polygon."
        self.assertIn(errmsg, str(response.content))

    def test_points_in_roi_api_post_bad_roi_jibberish(self):
        """If the roi in the post request does not form a valid polygon, an
        appropriate error should be thrown.

        """

        url = reverse("api:get_points_in_roi")
        data = {"roi": "some random string"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi could not be converted to a valid GEOS geometry."
        self.assertIn(errmsg, str(response.content))

    def test_points_in_roi_api_post_missing_roi(self):
        """If the post request does not have a roi element an appropriate
        error should be thrown.

        """
        url = reverse("api:get_points_in_roi")
        data = {}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # =====================================
    #     Projects Completely In ROI

    def test_projects_contained_in_roi_api_get_put_delete(self):
        """the projects contained in api is currently readonly, but requires a
        post request (which holds the roi). Any other request type should
        throw an error.

        """

        url = reverse("api:get_project_points_contained_in_roi")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_projects_contained_in_roi_api_post_good_roi_wkt(self):
        """If we pass in a valid roi as wkt, the api should return a list of
        projects that are completely contained in the roi.  It will not
        include projects without any points, or with points outside of the roi.

        """

        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": self.roi.wkt}
        response = self.client.post(url, data)
        request = self.factory.get(url)

        points = SamplePoint.objects.filter(project__prj_cd="LHA_IA16_INN")
        serializer = ProjectPointSerializer(
            points, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_projects_contained_in_roi_api_post_good_roi_json(self):
        """If we pass in a valid roi as json, the api should return a list of
        projects that are completely contained in the roi.  It will not
        include projects without any points, or with points outside of the roi.
        """
        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": self.roi.geojson}
        response = self.client.post(url, data)
        request = self.factory.get(url)

        points = SamplePoint.objects.filter(project__prj_cd="LHA_IA16_INN")
        serializer = ProjectPointSerializer(
            points, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_projects_contained_in_roi_api_post_no_points(self):
        """If we pass in a valid roi, that does not include any sample points,
        the api should return a message indicating that no projects were
        found in the roi.

        """

        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": self.roi2.wkt}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_projects_contained_in_roi_api_post_bad_roi_line(self):
        """If the roi in the post request does not form a valid polygon, an
        appropriate error should be thrown.
        """

        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": self.line.wkt}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi is not a valid polygon."
        self.assertIn(errmsg, str(response.content))

    def test_projects_contained_in_roi_api_post_bad_roi_point(self):
        """If the roi in the post request does not form a valid polygon (just
        a point in this test), an appropriate error should be thrown.

        """

        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": "POINT(-82.024922507764 44.0171801372301)"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi is not a valid polygon."
        self.assertIn(errmsg, str(response.content))

    def test_projects_contained_in_roi_api_post_bad_roi_jibberish(self):
        """If the roi in the post request does not form a valid polygon, (just
        jubberish in this test) an appropriate error should be thrown.
        """

        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": "some random string"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi could not be converted to a valid GEOS geometry."
        self.assertIn(errmsg, str(response.content))

    def test_projects_contained_in_roi_api_post_missing_roi(self):
        """If the post request does not have a roi element an appropriate
        error should be thrown.
        """

        url = reverse("api:get_project_points_contained_in_roi")
        data = {}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # =====================================
    #    Projects Partially In ROI

    def test_projects_partially_contained_in_roi_api_get_put_delete(self):
        """the projects partially contained in api is currently readonly, but
        requires a post request (which holds the roi). Any other request
        type should throw an error.

        """
        url = reverse("api:get_project_points_overlapping_roi")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_projects_partially_contained_in_roi_api_post_good_roi_wkt(self):
        """If we pass in a valid roi as wkt, the api should return a list of
        projects that are partially contained in the roi.  It will not
        include projects without any points, or projects with all of their
        points inside the roi.

        """

        url = reverse("api:get_project_points_overlapping_roi")
        data = {"roi": self.roi.wkt}
        response = self.client.post(url, data)
        request = self.factory.get(url)

        points = SamplePoint.objects.filter(project__prj_cd="LHA_IA16_LAP")
        serializer = ProjectPointSerializer(
            points, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_projects_partially_contained_in_roi_api_post_good_roi_json(self):
        """If we pass in a valid roi as json, the api should return a list of
        projects that are partially contained in the roi.  It will not
        include projects without any points, or projects with all of their
        points in the roi.

        """

        url = reverse("api:get_project_points_overlapping_roi")
        data = {"roi": self.roi.geojson}
        response = self.client.post(url, data)
        request = self.factory.get(url)

        points = SamplePoint.objects.filter(project__prj_cd="LHA_IA16_LAP")
        serializer = ProjectPointSerializer(
            points, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_projects_partially_contained_in_roi_api_post_no_points(self):
        """If we pass in a valid roi, that does not include any sample points,
        the api should return a message indicating that no samples from
        any project were found in the roi.

        """
        url = reverse("api:get_project_points_contained_in_roi")
        data = {"roi": self.roi2.wkt}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_projects_partially_contained_in_roi_api_post_bad_roi_line(self):
        """If the roi in the post request does not form a valid polygon (just
        a line in this test), an appropriate error should be thrown.

        """
        url = reverse("api:get_project_points_overlapping_roi")
        data = {"roi": self.line.wkt}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi is not a valid polygon."
        self.assertIn(errmsg, str(response.content))

    def test_projects_partially_contained_in_roi_api_post_bad_roi_point(self):
        """If the roi in the post request does not form a valid polygon (just
        a point in this test), an appropriate error should be thrown.

        """
        url = reverse("api:get_project_points_overlapping_roi")
        data = {"roi": "POINT(-82.024922507764 44.0171801372301)"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi is not a valid polygon."
        self.assertIn(errmsg, str(response.content))

    def test_projects_partially_contained_in_roi_api_post_bad_roi_junk(self):
        """If the roi in the post request does not form a valid polygon, (just
        jubberish in this test) an appropriate error should be thrown.
        """

        url = reverse("api:get_project_points_overlapping_roi")
        data = {"roi": "some random string"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        errmsg = "roi could not be converted to a valid GEOS geometry."
        self.assertIn(errmsg, str(response.content))

    def test_projects_partially_contained_in_roi_api_post_missing_roi(self):
        """If the post request does not have a roi element an appropriate
        error should be thrown.

        """
        url = reverse("api:get_project_points_overlapping_roi")
        data = {}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
