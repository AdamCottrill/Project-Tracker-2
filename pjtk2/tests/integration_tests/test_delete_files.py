from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import pre_save, post_save
from django.urls import reverse
from django_webtest import WebTest


from pjtk2.models import send_notice_prjms_changed, ProjectMilestones, Report
from pjtk2.tests.factories import (
    ProjectFactory,
    MilestoneFactory,
    ProjectMilestonesFactory,
    ReportFactory,
    UserFactory,
    EmployeeFactory,
    DBA_Factory,
)


from django.test.client import Client
from django.test import TestCase

# from django.http import Http404

import pytest

User = get_user_model()


@pytest.fixture(scope="module", autouse=True)
def disconnect_signals():
    """disconnect the signals before each test - not needed here"""
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)


class SisterWarningRendersonConfirmationPageTestCase(WebTest):
    """these tests will verify that the warning message statting that if
    the current project has one or more sisters, they could also be
    effected by deleting the report.

    It should only appear if the project has one or more sisters.

    """

    def setUp(self):
        """In every test, we will need a user, project, a milestone, a
        projectmilestone, and a report."""

        self.password = "Abcd1234"

        self.user = UserFactory(
            username="hsimpson",
            first_name="Homer",
            last_name="Simpson",
            password=self.password,
        )
        # self.Employee = EmployeeFactory(user=self.user)

        self.milestone = MilestoneFactory(
            label="Approved", category="Core", order=1, report=False
        )
        signoff = MilestoneFactory(label="Sign Off")
        # a required reports
        self.milestone = MilestoneFactory(
            label="Proposal Presentation", category="Core", order=2, report=True
        )

        self.project1 = ProjectFactory(prj_cd="LHA_IA14_111", owner=self.user)

        self.project2 = ProjectFactory(prj_cd="LHA_IA14_222", owner=self.user)

        self.project1.approve()
        self.project2.approve()

        # now we have to associate the report a report with our report
        # milestone.  the m2m relationship makes this a little tricky -
        # can't do it directly in factoryboy.
        # get our projectmilestone:
        self.pmst = self.project1.projectmilestones.get(
            milestone__label=self.milestone.label
        )

        # then make a report and associated the pmst with it
        self.report = ReportFactory.create()
        self.report.projectreport.add(self.pmst)
        self.report.save()

        ProjectMilestonesFactory(project=self.project1, milestone=signoff)
        ProjectMilestonesFactory(project=self.project2, milestone=signoff)

    def test_warning_message_renders(self):
        """Project 1 and 2 are sisters, when we try to delete the report
        associated with project1, we should see a warning message to
        that effect.

        """

        # make the project sisters
        self.project1.add_sister(self.project2.slug)

        response = self.app.get(
            reverse(
                "delete_report",
                kwargs={"slug": self.project1.slug, "pk": self.report.id},
            ),
            user=self.user,
        )
        self.assertEqual(response.status_int, 200)
        msg = (
            "This projects has sister projects that could be"
            + " affected by deleting this report!"
        )
        self.assertContains(response, msg)

    def test_warning_message_does_renders_without_sister(self):
        """If project 1 and 2 are not sisters, when we try to delete the
        report associated with project1, we should Not see the sister
        warning message.

        """

        url = reverse(
            "delete_report", kwargs={"slug": self.project1.slug, "pk": self.report.id}
        )
        response = self.app.get(url, user=self.user)

        self.assertEqual(response.status_int, 200)
        msg = (
            "This projects has sister projects that could be"
            + " affected by deleting this report!"
        )
        self.assertNotContains(response, msg)


class DeleteReportLinkOnDetailPageTestCase(WebTest):
    """These tests will verify that the delete report button renders on
    project detail appropriately.

    There are alos tests to verify that normal users cannot delete the
    report even if they try to access the url directly and that
    non-logged in users are redirected to a login page..

    """

    def setUp(self):
        """In every test, we will need a user, project, a milestone, a
        projectmilestone, and a report."""

        self.password = "Abcd1234"

        self.user = UserFactory(
            username="hsimpson",
            first_name="Homer",
            last_name="Simpson",
            password=self.password,
        )

        # a required reports
        self.milestone = MilestoneFactory.create(
            label="Proposal Presentation", category="Core", order=1, report=True
        )

        self.project = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)

        # now we have to associate the report a report with our report
        # milestone.  the m2m relationship makes this a little tricky -
        # can't do it directly in factoryboy.
        # get our projectmilestone:
        self.pmst = self.project.projectmilestones.get(
            milestone__label=self.milestone.label
        )

        # then make a report and associated the pmst with it
        self.report = ReportFactory.create()
        self.report.projectreport.add(self.pmst)
        self.report.save()

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def tearDown(self):
        pass

    def test_project_owner_has_delete_link(self):
        """If the logged user is the project lead, they should be able both
        download the file and delete it.  The project detail should
        contian a link to delete the file.
        """

        response = self.app.get(
            reverse("project_detail", args=(self.project.slug,)), user=self.user
        )
        self.assertEqual(response.status_int, 200)

        # our response should contain a link to our file:
        url = reverse("serve_file", kwargs={"filename": self.report.report_path})
        self.assertContains(response, url)

        # a link to delete our file
        url = reverse(
            "delete_report", kwargs={"slug": self.project.slug, "pk": self.report.id}
        )
        url = '<a href="{0}" class="btn btn-danger btn-sm" title="Delete Report" role="button">'.format(url)
        self.assertContains(response, url)

    def test_manager_has_delete_link(self):
        """If a logged in user who is a manager, they should be able both
        download the file and delete it.  The project detail should
        contian a link to delete the file.
        """

        self.user2 = UserFactory.create(
            username="mburns", first_name="Burns", last_name="Montgomery"
        )

        # make Mr. Burns the manager:
        EmployeeFactory(user=self.user2, role="manager")

        response = self.app.get(
            reverse("project_detail", args=(self.project.slug,)), user=self.user2
        )
        self.assertEqual(response.status_int, 200)

        # our response should contain a link to our file:
        url = reverse("serve_file", kwargs={"filename": self.report.report_path})
        self.assertContains(response, url)

        # a link to delete our file
        url = reverse(
            "delete_report", kwargs={"slug": self.project.slug, "pk": self.report.id}
        )
        url = '<a href="{0}" class="btn btn-danger btn-sm" title="Delete Report" role="button">'.format(url)
        self.assertContains(response, url)

    def test_admin_has_delete_link(self):

        """If a logged in user who is an administrator, they should be able both
        download the file and delete it.  The project detail should
        contian a link to delete the file.
        """

        self.user3 = DBA_Factory.create(
            username="bsimpson", first_name="Bart", last_name="Simpson"
        )

        response = self.app.get(
            reverse("project_detail", args=(self.project.slug,)), user=self.user3
        )
        self.assertEqual(response.status_int, 200)

        # our response should contain a link to our file:
        url = reverse("serve_file", kwargs={"filename": self.report.report_path})
        self.assertContains(response, url)

        # a link to delete our file
        url = reverse(
            "delete_report", kwargs={"slug": self.project.slug, "pk": self.report.id}
        )
        url = '<a href="{0}" class="btn btn-danger btn-sm" title="Delete Report" role="button">'.format(url)
        self.assertContains(response, url)

    def test_joe_user_does_not_have_delete_link(self):
        """If a logged in user who is not the project lead or a manager or an
        admin, they should have a link to download the report but not
        delete it.
        """

        self.user4 = UserFactory(
            username="bgumble", first_name="Barney", last_name="Gumble"
        )

        response = self.app.get(
            reverse("project_detail", args=(self.project.slug,)), user=self.user4
        )
        self.assertEqual(response.status_int, 200)

        # our response should contain a link to our file:
        url = reverse("serve_file", kwargs={"filename": self.report.report_path})
        self.assertContains(response, url)

        # a link to delete our file
        url = reverse(
            "delete_report", kwargs={"slug": self.project.slug, "pk": self.report.id}
        )
        url = '<a href="{0}">'.format(url)
        self.assertNotContains(response, url)

    def test_joe_user_cannot_access_delete_report_url(self):
        """If a logged in user who is not the project lead or a manager or an
        admin, they should be directed back to the project detail
        page if they try to access the delete report url directly.
        """

        self.user4 = UserFactory(
            username="bgumble", first_name="Barney", last_name="Gumble"
        )

        response = self.app.get(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            ),
            user=self.user4,
        ).follow()

        # make sure that we are successfully redirecte back to the
        # project detail page:
        self.assertEqual(response.status_int, 200)
        self.assertTemplateUsed("pjtk2/project_detail.html")
        self.assertContains(response, "Project Start:")
        self.assertContains(response, "Project End:")
        self.assertContains(response, "Reporting Requirements:")

    def test_anon_user_cannot_access_delete_report_url(self):
        """If a user is not logged in and try to access the delete report url
        directly, they should be directed back to the login page.
        """

        url = reverse(
            "delete_report", kwargs={"slug": self.project.slug, "pk": self.report.id}
        )
        response = self.app.get(url)
        # verify that they are re-directed
        self.assertEqual(response.status_int, 302)
        redirectstring = "{}?next={}".format(reverse("login"), url)

        self.assertRedirects(response, redirectstring)


class DeleteReportTestCase(TestCase):
    """These tests will verify that project owner, administrator and
    manager can infact delete reports.  Non-owners and non-logged in
    users cannot.

    """

    def setUp(self):
        """In every test, we will need a user, project, a milestone, a
        projectmilestone, and a report."""

        self.password = "Abcd1234"

        self.user = UserFactory(
            username="hsimpson",
            first_name="Homer",
            last_name="Simpson",
            password=self.password,
        )

        # a required reports
        self.milestone = MilestoneFactory.create(
            label="Proposal Presentation", category="Core", order=1, report=True
        )

        self.project = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)

        # now we have to associate the report a report with our report
        # milestone.  the m2m relationship makes this a little tricky -
        # can't do it directly in factoryboy.
        # get our projectmilestone:
        self.pmst = self.project.projectmilestones.get(
            milestone__label=self.milestone.label
        )

        # then make a report and associated the pmst with it
        self.report = ReportFactory.create()
        self.report.projectreport.add(self.pmst)
        self.report.save()

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def tearDown(self):
        pass

    def test_delete_report_for_project_does_not_exists(self):
        """If the user tries to delete a report for project that does not
        exist, a 404 should be thrown.
        """

        login = self.client.login(username=self.user.username, password=self.password)
        self.assertTrue(login)

        response = self.client.get(
            reverse(
                "delete_report", kwargs={"slug": "zzz_zz12_123", "pk": self.report.id}
            )
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_report_that_does_not_exists(self):
        """If the user tries to delete a report that does not exist, a 404
        should be thrown.
        """

        login = self.client.login(username=self.user.username, password=self.password)
        self.assertTrue(login)

        response = self.client.get(
            reverse("delete_report", kwargs={"slug": self.project.slug, "pk": 999999})
        )
        self.assertEqual(response.status_code, 404)

    def test_project_owner_can_delete_report_get(self):
        """If the logged user is the project lead, they should be able
        successfully access the delete file page.
        """

        login = self.client.login(username=self.user.username, password=self.password)
        self.assertTrue(login)

        response = self.client.get(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("pjtk2/confirm_report_delete.html")

    def test_project_owner_can_delete_report_post(self):
        """If the logged user is the project lead, they should be successfully
        click on the confirm delete button and delete the report.

        """

        login = self.client.login(username=self.user.username, password=self.password)
        self.assertTrue(login)

        response = self.client.post(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed("pjtk2/project_detail.html")
        id = self.report.id
        self.assertFalse(Report.objects.filter(id=id).exists())

    def test_manager_can_delete_report_get(self):
        """A manager should be able to access the delete file page.
        """

        self.user2 = UserFactory.create(
            username="mburns",
            first_name="Burns",
            last_name="Montgomery",
            password=self.password,
        )

        # make Mr. Burns the manager:
        EmployeeFactory(user=self.user2, role="manager")

        login = self.client.login(username=self.user2.username, password=self.password)
        self.assertTrue(login)

        response = self.client.get(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("pjtk2/confirm_report_delete.html")

    def test_manager_can_delete_report_post(self):
        """If a logged in user who is a manager, they should be able to
        successfully submit the confirm delelte button and delete the
        report.
        """

        self.user2 = UserFactory.create(
            username="mburns",
            first_name="Burns",
            last_name="Montgomery",
            password=self.password,
        )

        # make Mr. Burns the manager:
        EmployeeFactory(user=self.user2, role="manager")

        login = self.client.login(username=self.user2.username, password=self.password)
        self.assertTrue(login)

        response = self.client.post(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        # make sure that we are redirected to the project detail page
        # and that the report has been deleted from the database.
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed("pjtk2/project_detail.html")
        id = self.report.id
        self.assertFalse(Report.objects.filter(id=id).exists())

    def test_admin_can_delete_report_get(self):

        """If a logged in user is an administrator, they should be able to
        successfully access the delete file page.
        """

        self.user3 = DBA_Factory.create(
            username="bsimpson",
            first_name="Bart",
            last_name="Simpson",
            password=self.password,
        )

        login = self.client.login(username=self.user3.username, password=self.password)
        self.assertTrue(login)

        response = self.client.get(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed("pjtk2/confirm_report_delete.html")

    def test_admin_can_delete_report_post(self):

        """If a logged in user is an administrator, they should be able to
        successfully confirm that they want to delete file and then
        successfully delete the file.
        """

        self.user3 = DBA_Factory.create(
            username="bsimpson",
            first_name="Bart",
            last_name="Simpson",
            password=self.password,
        )

        login = self.client.login(username=self.user3.username, password=self.password)
        self.assertTrue(login)

        response = self.client.post(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        # make sure that we are redirected to the project detail page
        # and that the report has been deleted from the database.
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed("pjtk2/project_detail.html")
        id = self.report.id
        self.assertFalse(Report.objects.filter(id=id).exists())

    def test_joe_user_cannot_delete_report_get(self):
        """If a logged in user who is not the project lead or a manager or an
        admin, they should have a link to download the report but not
        delete it.
        """

        self.user4 = UserFactory(
            username="bgumble",
            first_name="Barney",
            last_name="Gumble",
            password=self.password,
        )

        login = self.client.login(username=self.user4.username, password=self.password)
        self.assertTrue(login)

        response = self.client.get(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed("pjtk2/project_detail.html")

    def test_joe_user_cannot_delete_report_post(self):
        """If somehow, joe user is able to submit a post request to the delete
        file view, he will be re-directed to the detail page and the
        file will not be deleted.

        """

        self.user4 = UserFactory(
            username="bgumble",
            first_name="Barney",
            last_name="Gumble",
            password=self.password,
        )

        login = self.client.login(username=self.user4.username, password=self.password)
        self.assertTrue(login)

        response = self.client.post(
            reverse(
                "delete_report",
                kwargs={"slug": self.project.slug, "pk": self.report.id},
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed("pjtk2/project_detail.html")

        # make sure that the report is still there
        id = self.report.id
        self.assertTrue(Report.objects.filter(id=id).exists())
