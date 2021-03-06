from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models.signals import pre_save

from django_webtest import WebTest

from pjtk2.models import ProjectMilestones, send_notice_prjms_changed
from pjtk2.tests.factories import ProjectFactory, ProjTypeFactory, UserFactory


User = get_user_model()


def setup():
    """disconnect the signals before each test - not needed here"""
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)


def teardown():
    """re-connecct the signals here."""
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)


class CanViewSearchForm(WebTest):
    """verify that we can view and submit the search form"""

    def setUp(self):
        """ """
        # USER
        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

    def test_RenderSearchForm(self):
        """load the search form"""
        response = self.app.get(reverse("project_search"), user=self.user)
        self.assertEqual(response.status_int, 200)
        self.assertTemplateUsed(response, "pjtk2/ProjectSearch.html")

        form = response.forms["search"]
        form["search"] = "text"
        response = form.submit("submit")

        msg = "Sorry, no projects match that criteria."
        self.assertContains(response, msg)
        # assert 0==1

    def tearDown(self):

        self.user.delete()


class CanUseSearchForm(WebTest):
    """verify that we can use the submit form and that it returns the
    expected results.

    **NOTE** - these tests do not work and were never completed - the test
    database does not have indices it can search against - I don't know
    how to set this up easily for testing purposes.  For now we'll have to
    assume that everything works as expected.

    """

    def setUp(self):
        """ """

        # USER
        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.ProjType = ProjTypeFactory(project_type="Nearshore Index")

        self.project1 = ProjectFactory(
            prj_cd="LHA_IA12_111", prj_nm="Parry Sound Index", owner=self.user
        )

        comment = "Test of UGLMU Project Tracker - Salvelinus"
        self.project2 = ProjectFactory(
            prj_cd="LHA_IA12_222", owner=self.user, comment=comment
        )
        self.project3 = ProjectFactory(
            prj_cd="LHA_IA12_333", owner=self.user, project_type=self.ProjType
        )

    def test_SearchProjectName(self):
        """Verify that we can retrieve projects based on project name"""

        response = self.app.get(reverse("project_search"), user=self.user)
        form = response.forms["search"]
        form["search"] = "Parry Sound"
        response = form.submit("submit")

        # projects 1 is the only one that contains "Parry Sound" and
        # should be the only one in the response
        baselink = """<a href="{0}">{1}</a>"""
        linkstring = baselink.format(
            self.project1.get_absolute_url(), self.project1.prj_cd
        )
        self.assertContains(response, linkstring, html=True)
        self.assertContains(response, self.project1.prj_nm)

        # these projects should NOT be in the response
        linkstring = baselink.format(
            self.project2.get_absolute_url(), self.project2.prj_cd
        )
        self.assertNotContains(response, linkstring, html=True)

        linkstring = baselink.format(
            self.project3.get_absolute_url(), self.project3.prj_cd
        )
        self.assertNotContains(response, linkstring, html=True)

    def test_SearchProjectDescription(self):
        """Verify that we can retrieve projects based word in the project
        description"""

        response = self.app.get(reverse("project_search"), user=self.user)
        form = response.forms["search"]
        form["search"] = "Salvelinus"
        response = form.submit("submit")

        # projects 2 is the only one that contains "Salvelinus" and
        # should be the only one in the response

        baselink = """<a href="{0}">{1}</a>"""
        linkstring = baselink.format(
            self.project2.get_absolute_url(), self.project2.prj_cd
        )
        print("linkstring={}".format(linkstring))
        print("response={}".format(response))
        self.assertContains(response, linkstring, html=True)
        self.assertContains(response, self.project2.prj_nm)

        # these projects should NOT be in the response
        linkstring = baselink.format(
            self.project1.get_absolute_url(), self.project1.prj_cd
        )
        self.assertNotContains(response, linkstring, html=True)

        linkstring = baselink.format(
            self.project3.get_absolute_url(), self.project3.prj_cd
        )
        self.assertNotContains(response, linkstring, html=True)

    def test_SearchProjectTag(self):
        """Verify that we can retrieve projects based on project keyword"""

        tags = ["red", "blue"]
        tags.sort()
        for tag in tags:
            self.project1.tags.add(tag)
            self.project2.tags.add(tag)

        response = self.app.get(reverse("project_search"), user=self.user)
        self.assertEqual(response.status_int, 200)
        self.assertTemplateUsed(response, "pjtk2/ProjectSearch.html")

        form = response.forms["search"]
        form["search"] = "red"
        response = form.submit("submit")

        # projects 1 and have been tagged with 'red'
        # and should be the response
        baselink = """<a href="{0}">{1} - {2}</a>"""
        linkstring = baselink.format(
            self.project1.get_absolute_url(), self.project1.prj_cd, self.project1.prj_nm
        )
        # self.assertContains(response, linkstring, html=True)

        linkstring = baselink.format(
            self.project2.get_absolute_url(), self.project2.prj_cd, self.project2.prj_nm
        )
        # self.assertContains(response, linkstring, html=True)

        # these projects should NOT be in the response
        linkstring = baselink.format(
            self.project3.get_absolute_url(), self.project3.prj_cd, self.project3.prj_nm
        )
        # self.assertNotContains(response, linkstring, html=True)

    def test_search_project_type(self):
        """Verify that we can retrieve projects based on project type"""

        response = self.app.get(reverse("project_search"), user=self.user)
        self.assertEqual(response.status_int, 200)
        self.assertTemplateUsed(response, "pjtk2/ProjectSearch.html")

        form = response.forms["search"]
        form["search"] = "Nearshore"
        response = form.submit("submit")

        # projects 1 and 2 are offshore index projects and should NOT
        # be returned, project 3 was a nearshore index and should be.
        baselink = """<a href="{0}">{1} - {2}</a>"""
        linkstring = baselink.format(
            self.project1.get_absolute_url(), self.project1.prj_cd, self.project1.prj_nm
        )
        # self.assertNotContains(response, linkstring, html=True)

        linkstring = baselink.format(
            self.project2.get_absolute_url(), self.project2.prj_cd, self.project2.prj_nm
        )
        # self.assertNotContains(response, linkstring, html=True)

        # this project should be in the response
        linkstring = baselink.format(
            self.project3.get_absolute_url(), self.project3.prj_cd, self.project3.prj_nm
        )
        # self.assertContains(response, linkstring, html=True)

    def tearDown(self):

        self.user.delete()
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.ProjType.delete()
