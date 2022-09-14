import pytest
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import RequestFactory
from django.urls import reverse
from pjtk2.api.serializers import (
    ProjectSerializer,
    ProjectTypeSerializer,
    UserSerializer,
)
from pjtk2.models import Project, ProjectType
from pjtk2.tests.factories import ProjectFactory, ProjTypeFactory, UserFactory
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ProjectAPITest(APITestCase):
    def setUp(self):

        self.factory = RequestFactory()

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.ProjectType1 = ProjTypeFactory.create(project_type="Fake Project")

        self.ProjectType2 = ProjTypeFactory.create(project_type="Another Project")

        # define these as strings here so that we can access them later
        # and verify that the returned values match.
        self.commentStr = "This is a fake comment."
        self.ProjectName = "Homer's Odyssey"

        # we need to create some models with different years - starting
        # with the current year.
        self.year = 2011
        prj_cd = "LHA_IA%s_111" % str(self.year)[-2:]
        self.project1 = ProjectFactory.create(
            prj_cd=prj_cd,
            owner=self.user,
            comment=self.commentStr,
            project_type=self.ProjectType1,
            prj_nm=self.ProjectName,
        )

        prj_cd = "LHA_IA%s_222" % str(self.year - 1)[-2:]
        self.project2 = ProjectFactory.create(
            prj_cd=prj_cd, owner=self.user, project_type=self.ProjectType2
        )

        prj_cd = "LHA_IA%s_333" % str(self.year - 2)[-2:]
        self.project3 = ProjectFactory.create(prj_cd=prj_cd, owner=self.user)

    # =================================
    #     PROJECT LIST

    def test_project_list_api_get(self):
        """If we access our project list api using a get request, the response
        will return a series of json objects representing the projects in
        our database.

        """
        # get API response for our project
        url = reverse("api:project-list")
        request = self.factory.get(url)
        response = self.client.get(url)

        # get data from db
        projects = Project.objects.all()
        serializer = ProjectSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_list_api_post_put_delete(self):
        """the project list api is currently readonly - any other request
        type should throw an error.

        """

        url = reverse("api:project-list")
        data = {"name": "DabApps"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_project_list_api_get_filter_first_year(self):
        """The project list api accepts url filters for first_year - if the
        filter is included in the url, the resposne should only return
        projects that occur ON or after the specified year.  The response
        should be a series of json objects that satisfy that criteria.

        """

        first_year = self.year - 1
        baseurl = reverse("api:project-list")
        query_string = "?first_year={}".format(first_year)
        url = baseurl + query_string
        request = self.factory.get(url)
        response = self.client.get(url)

        projects = Project.objects.filter(year__gte=first_year)
        serializer = ProjectSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_list_api_get_filter_last_year(self):
        """The project list api accepts url filters for last_year - if the
        filter is included in the url, the response should only return
        projects that occur ON or before the specified year.  The response
        should be a series of json objects that satisfy that criteria.

        """

        last_year = self.year - 1
        baseurl = reverse("api:project-list")
        query_string = "?last_year={}".format(last_year)
        url = baseurl + query_string
        request = self.factory.get(url)
        response = self.client.get(url)

        projects = Project.objects.filter(year__lte=last_year)
        serializer = ProjectSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_list_api_get_filter_first_and_last_year(self):
        """The project list api accepts url filters for first and last year -
         if the filters are included in the url, the response should only
        return projects that occur between the specified years (including
         first and last year). The response should be a series of json
         objects that satisfy that criteria.

        """

        the_year = self.year - 1

        baseurl = reverse("api:project-list")
        query_string = "?first_year={}&last_year={}".format(the_year, the_year)
        url = baseurl + query_string
        request = self.factory.get(url)
        response = self.client.get(url)

        projects = Project.objects.filter(year=the_year)

        serializer = ProjectSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_list_api_get_filter_project_type(self):
        """The project list api accepts url filters for project_type - if the
        filter is included in the url, the response should only return
        projects of that project type.  The response
        should be a series of json objects that satisfy that criteria.

        """

        baseurl = reverse("api:project-list")
        query_string = "?project_type={}".format(self.ProjectType1.id)
        url = baseurl + query_string
        request = self.factory.get(url)
        response = self.client.get(url)

        projects = Project.objects.filter(project_type=self.ProjectType1)

        serializer = ProjectSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_list_api_get_filter_multiple_project_types(self):
        """The project list api accepts url filters for project_type - if the
        filter is included in the url, the response should only return
        projects of that project types.  Multiple project types can be
        submitted in the request. The response should be a series of json
        objects that satisfy that criteria.

        """
        baseurl = reverse("api:project-list")
        query_string = "?project_type={},{}".format(
            self.ProjectType1.id, self.ProjectType2.id
        )
        url = baseurl + query_string
        request = self.factory.get(url)
        response = self.client.get(url)

        projects = Project.objects.filter(
            project_type__in=(self.ProjectType1, self.ProjectType2)
        )

        serializer = ProjectSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    # =================================
    #       PROJECT DETAIL

    def test_project_detail_api_get_good_project_code(self):
        """If we access our project detail api using a get request and a good
        project code code, the response will return a json object
        containing the project code, project name, start date, end date,
        and project description.

        """
        slug = self.project1.slug
        url = reverse("api:project-detail", kwargs={"slug": slug})
        request = self.factory.get(url)
        response = self.client.get(url)

        # get data from db
        projects = Project.objects.get(slug=slug)
        serializer = ProjectSerializer(projects, context={"request": request})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print("response.data={}".format(response.data))
        print("serializer.data={}".format(serializer.data))

        self.assertEqual(response.data, serializer.data)

    def test_project_detail_api_get_bad_project_code(self):
        """If we try to access the project detail api with a malformed project
        code it will return an error.

        """
        slug = "LHA_IA99_00"
        url = reverse("api:project-detail", kwargs={"slug": slug})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_project_detail_api_get_project_code_doesnot_exist(self):
        """If we try to access the project detail api with a malformed project
        code it will return a 404 error.

        """

        slug = "LHA_IA99_000"
        url = reverse("api:project-detail", kwargs={"slug": slug})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_project_detail_api_post_put_delete(self):
        """the project detail api is currently readonly - any other request
        type should throw an error.

        """

        slug = "LHA_IA99_000"
        url = reverse("api:project-detail", kwargs={"slug": slug})
        data = {"prj_nm": "Fake Project"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # =================================
    #     PROJECT_TYPE LIST

    def test_project_type_list_api_get(self):
        """If we access our project_type list api using a get request,
        the response will return a series of json objects representing
        the project_types in our database.

        """
        url = reverse("api:project_type-list")
        request = self.factory.get(url)
        response = self.client.get(url)

        # get data from db
        projects = ProjectType.objects.all()
        serializer = ProjectTypeSerializer(
            projects, many=True, context={"request": request}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_type_list_api_post_put_delete(self):
        """the project_type list api is currently readonly - any other request
        type should throw an error.

        """
        url = reverse("api:project_type-list")
        data = {"name": "DabApps"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_project_type_detail_api_get(self):
        """If we access our project_type list api using a get request,
        the response will return a series of json objects representing
        the project_types in our database.

        """
        id = self.ProjectType1.id
        url = reverse("api:project_type-detail", kwargs={"pk": id})
        request = self.factory.get(url)
        response = self.client.get(url)

        # get data from db
        project_type = ProjectType.objects.get(id=id)
        serializer = ProjectTypeSerializer(project_type, context={"request": request})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_project_type_detail_api_post_put_delete(self):
        """the project_type list api is currently readonly - any other request
        type should throw an error.

        """
        id = self.ProjectType1.id
        url = reverse("api:project_type-detail", kwargs={"pk": id})
        data = {"project_type": "Fake Project Type"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # =================================
    #     PROJECT_LEAD LIST

    def test_project_lead_list_api_get(self):
        """If we access our project_lead list api using a get request,
        the response will return a series of json objects representing
        the project_leads in our database.

        """
        url = reverse("api:project_lead-list")
        request = self.factory.get(url)
        response = self.client.get(url)

        # get data from db
        users = User.objects.all()
        serializer = UserSerializer(users, many=True, context={"request": request})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_project_lead_list_api_post_put_delete(self):
        """the project_lead list api is currently readonly - any other request
        type should throw an error.

        """
        url = reverse("api:project_lead-list")
        data = {"name": "DabApps"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_project_lead_detail_api_get(self):
        """If we access our project_lead list api using a get request,
        the response will return a series of json objects representing
        the project_leads in our database.

        """
        username = self.user.username
        url = reverse("api:project_lead-detail", kwargs={"username": username})
        request = self.factory.get(url)
        response = self.client.get(url)

        # get data from db
        my_user = User.objects.get(username=username)
        serializer = UserSerializer(my_user, context={"request": request})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_project_lead_detail_api_post_put_delete(self):
        """the project_lead list api is currently readonly - any other request
        type should throw an error.

        """
        username = self.user.username
        url = reverse("api:project_lead-detail", kwargs={"username": username})
        data = {"username": "MickyMouse"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
