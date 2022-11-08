import unittest
from datetime import datetime

import pytest
import pytz
from django.contrib.auth import get_user, get_user_model
from django.db.models.signals import pre_save
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from pjtk2.models import (
    Milestone,
    Project,
    ProjectMilestones,
    send_notice_prjms_changed,
)
from pjtk2.tests.factories import (
    EmployeeFactory,
    FundingSourceFactory,
    MilestoneFactory,
    ProjectFactory,
    ProjectFundingFactory,
    ProjectMilestonesFactory,
    UserFactory,
)
from pjtk2.utils.helpers import is_dba, is_manager
from pjtk2.views import can_edit

# from pjtk2.functions import can_edit
User = get_user_model()


@pytest.fixture(scope="module", autouse=True)
def disconnect_signals():
    """disconnect the signals before each test - not needed here"""
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)


# def setup():
#    '''disconnect the signals before each test - not needed here'''
#    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)
#
# def teardown():
#    '''re-connecct the signals here.'''
#    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)
#


class TestCanEditFunction(TestCase):
    """a simple test to verify that the function can_edit() returns a
    boolean value indicating whether or not a user is allowed to edit a
    particular project.  Currently only managers and project owners can
    edit a project, other users are not."""

    def setUp(self):
        """Create three users, one project owner, one manager, and one regular
        user."""
        self.user1 = UserFactory.create(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.user2 = UserFactory.create(
            username="mburns", first_name="Burns", last_name="Montgomery"
        )

        self.user3 = UserFactory.create(
            username="bgumble", first_name="Barney", last_name="Gumble"
        )

        # make Mr. Burns the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user2.groups.add(managerGrp)
        EmployeeFactory(user=self.user2, role="manager")

        # PROJECTS
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user1)

        self.project2 = ProjectFactory.create(
            prj_cd="LHA_IA12_222", owner=self.user1, field_ldr=self.user3
        )

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project1, milestone=signoff)
        ProjectMilestonesFactory(project=self.project2, milestone=signoff)

    def test_can_edit_function(self):
        """Verify that canEdit returns the expected value given our project
        and each of the three users and their roles."""

        # as project owner, Homer can edit the project
        self.assertEqual(can_edit(self.user1, self.project1), True)
        # as a manageer, Mr Burns can edit the project too
        self.assertEqual(can_edit(self.user2, self.project1), True)
        # Barney can't edit project
        self.assertEqual(can_edit(self.user3, self.project1), False)

        # Project2
        # as project owner, Homer can edit the project
        self.assertEqual(can_edit(self.user1, self.project2), True)
        # as a manageer, Mr Burns can edit the project too
        self.assertEqual(can_edit(self.user2, self.project2), True)
        # but Barney Can edit project2 since he is the field leader:
        self.assertEqual(can_edit(self.user3, self.project2), True)

    def tearDown(self):
        """Clean up"""
        self.project2.delete()
        self.project1.delete()
        self.user3.delete()
        self.user2.delete()
        self.user1.delete()


###Views
##class IndexViewTestCase(TestCase):
##    '''verfiy that we can view the site index page'''
##    def test_index(self):
##        response = self.client.get('',follow=True)
##        self.assertEqual(response.status_code, 200)
##        self.assertTemplateUsed(response, 'ProjectList.html')
##        #self.assertContains(response, 'Site Index')
##        #self.assertContains(response, 'Project List')
##        #self.assertContains(response, 'Approved Project List')
##        #self.assertContains(response, 'Approve Projects')


class ProjectListTestCase(TestCase):
    """verfiy that we view the  project list, but only after logging-in"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()

    def test_without_Login_base_template_contents(self):
        """Users who are not logged in should be able to see the proejct list
        (Note - this was changed on July 16, 2014.  Previous version
        of pjtk2 required login for all views.)
        """
        response = self.client.get(reverse("ProjectList"), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/ProjectList.html")
        self.assertContains(response, "Projects")

        # verify that base template is rendered properly:
        # is should not contain the terms:
        self.assertNotContains(response, "New Project")
        self.assertNotContains(response, "My Projects")
        self.assertNotContains(response, "Approve Projects")
        self.assertNotContains(response, "Admin")
        self.assertNotContains(response, "Logout")
        self.assertNotContains(response, "Welcome")

    def test_bad_Password_Login(self):
        """verify that the login actually stops someone"""
        login = self.client.login(username=self.user.username, password="Wrong1234")
        self.assertFalse(login)

    def test_with_Login(self):
        """if we login with a valid user, we will be allowed to view
        the page"""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("ProjectList"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/ProjectList.html")
        self.assertContains(response, "Projects")

    def test_NewProject_on_Login(self):
        """if we login with a valid user, the template should contain a link
        to create a new project.
        """
        self.user.is_staff = True
        self.user.save()
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ProjectList"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New Project")
        self.assertContains(response, reverse("NewProject"))

    def tearDown(self):
        self.user.delete()


class CreateManagerTestCase(TestCase):
    """verify that we can create a user that belongs to the 'manager'
    group"""

    def setUp(self):
        self.user1 = UserFactory()
        EmployeeFactory(user=self.user1, role="manager")
        self.user2 = UserFactory()

    def test_is_manager(self):
        # grpcnt = self.user.groups.filter(name="manager").count()
        self.assertTrue(is_manager(self.user1))
        self.assertFalse(is_manager(self.user2))

    def tearDown(self):
        self.user1.delete()
        self.user2.delete()


class IsDbaTestCase(TestCase):
    """verify that we can create a use that belongs to the 'dba'
    group"""

    def setUp(self):
        self.user1 = UserFactory()
        EmployeeFactory(user=self.user1, role="dba")
        self.user2 = UserFactory()

    def test_is_dba(self):
        self.assertTrue(is_dba(self.user1))
        self.assertFalse(is_dba(self.user2))

    def tearDown(self):
        self.user1.delete()
        self.user2.delete()


class LoginTestCase(TestCase):
    """verify that we can login using a 'User' object"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            "john2", "lennon@thebeatles.com", "johnpassword"
        )

    def testLogin(self):
        self.client.login(username="john2", password="johnpassword")
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        self.user.delete()


class LogoutTestCase(TestCase):
    """verify that we can logout using a 'User' object"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(username="hsimpson")

    def testLogout(self):
        # first login a user
        login = self.client.login(username="hsimpson", password="Abcd1234")
        response = self.client.get(reverse("login"))

        user = get_user(self.client)
        assert user.is_authenticated is True

        self.assertEqual(response.status_code, 200)
        self.assertTrue(login)

        # now log them out:
        response = self.client.get(reverse("logout"), follow=True)
        self.assertEqual(response.status_code, 200)

        user = get_user(self.client)
        assert user.is_authenticated is False

    def tearDown(self):
        self.user.delete()


class FactoryBoyLoginTestCase(unittest.TestCase):
    """verify that we can login a user created with factory boy."""

    def setUp(self):
        self.client = Client()
        self.password = "Abcd1234"
        self.user = UserFactory.create(password=self.password)

    @pytest.mark.django_db()
    def testLogin(self):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        pass
        # self.user.delete()


# ================================
# PROJECT DETAIL VIEWS
class ProjectDetailownerTestCase(TestCase):
    """verify that a project owner can see the project and make
    appropriated changes, but not those available only to managers"""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.project = ProjectFactory(owner=self.user)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def test_with_Login(self):
        """if we login with a valid user, we will be allowed to view
        the page"""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")
        # self.assertContains(response, 'Project Detail')
        self.assertContains(response, self.project.prj_cd)
        self.assertContains(response, self.project.prj_nm)
        prj_ldr = "{0} {1}".format(
            self.project.prj_ldr.first_name, self.project.prj_ldr.last_name
        )
        self.assertContains(response, prj_ldr)
        self.assertContains(response, "Milestones")
        self.assertContains(response, "Reporting Requirements")

        # a user should be able to edit their own records, but not
        # update milestones.
        self.assertTrue(response.context["edit"])
        self.assertFalse(response.context["manager"])

    def test_without_Login(self):
        """Users who are not logged in, should be able to see theproject
        details, but should not see links to edit, copy or bookmark
        project or create a new one.  (Note - this was changed on July
        16, 2014.  Previous version of pjtk2 required login for all
        views.)

        """
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertNotContains(response, "Edit Information")
        self.assertNotContains(response, "Copy Project")
        self.assertNotContains(response, "Sister Projects")
        self.assertNotContains(response, "Bookmark Project")
        self.assertNotContains(response, "Upload Reports")
        self.assertNotContains(response, "Upload Assoc. Files")

    def tearDown(self):
        self.project.delete()
        self.user.delete()


class ProjectTeamMembersProjectDetail(TestCase):
    """Verify that the team members are included on the project detail
    page when a team is associated with a project."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(first_name="Homer", last_name="Simpson")

        # some project team members:
        self.user_lisa = UserFactory(
            username="lsimpson", first_name="Lisa", last_name="Simpson"
        )
        self.user_bart = UserFactory(
            username="bsimpson", first_name="Bart", last_name="Simpson"
        )
        self.user_maggie = UserFactory(
            username="msimpson", first_name="Maggie", last_name="Simpson"
        )

        self.project = ProjectFactory(prj_ldr=self.user, dba=self.user, owner=self.user)

        self.project2 = ProjectFactory(
            prj_cd="LHA_IA17_123", prj_ldr=self.user, dba=self.user, owner=self.user
        )

        # add Lisa and Bart to the team for project2. Don't add Maggie
        # to any team.
        self.project2.project_team.add(self.user_bart)
        self.project2.project_team.add(self.user_lisa)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)
        ProjectMilestonesFactory(project=self.project2, milestone=signoff)

    def test_project_without_team(self):
        """If we view a the details for a project without a team, it should
        not contiain the phrase "Team Members:"
        """
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertNotContains(response, "Project Team:")
        self.assertNotContains(response, "Bart Simpson")
        self.assertNotContains(response, "Lisa Simpson")
        self.assertNotContains(response, "Maggie Simpson")

    def test_project_wit_team(self):
        """If we view a the details for a project with a team, it should
        contiain the phrase "Team Members:" as well as each of their names.
        """
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project2.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertContains(response, "Project Team:")
        self.assertContains(response, "Bart Simpson")
        self.assertContains(response, "Lisa Simpson")
        # maggie was not on the team and should not be in the response
        self.assertNotContains(response, "Maggie Simpson")

    def tearDown(self):
        self.project.delete()
        self.user.delete()


class ProjectDetailJoeUserTestCase(TestCase):
    """verify that a user who is not the owner can see the project but
    will be unable to edit any fields, upload reports or set
    milestones."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(
            username="gconstansa", first_name="George", last_name="Costansa"
        )
        # now create a project using a different user
        self.owner = UserFactory()
        self.project = ProjectFactory(owner=self.owner)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def test_with_Login(self):
        """if we login with a valid user, we will be allowed to view
        the page"""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")
        # self.assertContains(response, 'Project Detail')
        self.assertContains(response, self.project.prj_cd)
        self.assertContains(response, self.project.prj_nm)
        prj_ldr = "{0} {1}".format(
            self.project.prj_ldr.first_name, self.project.prj_ldr.last_name
        )
        self.assertContains(response, prj_ldr)
        self.assertContains(response, "Milestones")
        self.assertContains(response, "Reporting Requirements")

        # a user should be able to edit their own records, but not
        # update milestones.
        self.assertFalse(response.context["edit"])
        self.assertFalse(response.context["manager"])

    def tearDown(self):
        self.project.delete()
        self.owner.delete()
        self.user.delete()


class CancelProjectTestCase(TestCase):
    """verify that a manager can see a project and be able to both
    edit the record and update milestones."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(
            username="gcostansa", first_name="George", last_name="Costansa"
        )

        self.user1 = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # make george the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user.groups.add(managerGrp)
        EmployeeFactory(user=self.user, role="manager")

        self.ms = MilestoneFactory.create(
            label="Cancelled", protected=True, category="Core", order=99, report=False
        )

        # now create a project using a different user
        self.owner = UserFactory()
        self.project = ProjectFactory(owner=self.owner)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def test_manager_can_cancel_project(self):
        """A manager should be able to access the cancel project url and
        successfully cancel a project.
        """
        # make sure the project isn't cancelled to start with
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.cancelled)

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("cancel_project", kwargs={"slug": self.project.slug}), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        msg = "This project was cancelled."
        self.assertContains(response, msg)

        # it should be cancelled now:
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.cancelled)
        self.assertEqual(proj.cancelled_by, self.user)
        self.assertEqual(proj.status, "cancelled")

        # verify that the projectmilestone was created and has been populated
        pms = ProjectMilestones.objects.get(project=self.project, milestone=self.ms)
        # I don't know what time it will be, but it should populated with a
        # datetime object
        self.assertTrue(pms.completed != None)
        self.assertTrue(pms.completed.__class__ == datetime)

    def test_user_cannot_cancel_project(self):
        """A regular user cannot access the cancel project url and should be
        re-directed to project detail page.

        """
        # make sure the project isn't cancelled to start with
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.cancelled)

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("cancel_project", kwargs={"slug": self.project.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        msg = "This project was cancelled."
        self.assertNotContains(response, msg)

        # it still should not be cancelled :
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.cancelled)
        self.assertIsNone(proj.cancelled_by)
        self.assertNotEqual(proj.status, "cancelled")

    def test_anonuser_cannot_cancel_project(self):
        """An anonmous user cannot access the cancel project url and should be
        re-directed to login-page.

        """
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.cancelled)

        # login = self.client.login(username=self.user1.username,
        #                          password='Abcd1234')
        # self.assertTrue(login)
        response = self.client.get(
            reverse("cancel_project", kwargs={"slug": self.project.slug}), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        # it still should not be cancelled :
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.cancelled)

        self.assertIsNone(proj.cancelled_by)
        self.assertNotEqual(proj.status, "cancelled")

    def tearDown(self):
        self.project.delete()
        self.user1.delete()
        self.user.delete()


class UncancelProjectTestCase(TestCase):
    """verify that a manager can uncancel a cancelled project."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(
            username="gcostansa", first_name="George", last_name="Costansa"
        )

        self.user1 = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # make george the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user.groups.add(managerGrp)
        EmployeeFactory(user=self.user, role="manager")

        self.ms = MilestoneFactory.create(
            label="Cancelled", protected=True, category="Core", order=99, report=False
        )

        # now create a project using a different user
        self.owner = UserFactory()
        self.project = ProjectFactory(owner=self.owner)

        self.project.cancel(self.user)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def test_manager_can_uncancel_project(self):
        """A manager should be able to access the cancel project url and
        successfully cancel a project.
        """
        # make sure the project isn't cancelled to start with
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.cancelled)

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("uncancel_project", kwargs={"slug": self.project.slug}), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        msg = "This project was cancelled."
        self.assertNotContains(response, msg)

        # it is no longer cancelled:
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.cancelled)
        self.assertIsNone(proj.cancelled_by)
        self.assertEqual(proj.status, "ongoing")

    def test_user_cannot_uncancel_project(self):
        """A regular user cannot uncancel a project url and should be
        re-directed to project detail page.

        """
        # make sure the project isn't cancelled to start with
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.cancelled)

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("uncancel_project", kwargs={"slug": self.project.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        msg = "This project was cancelled."
        self.assertContains(response, msg)

        # it still should not be cancelled :
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.cancelled)
        self.assertEqual(proj.status, "cancelled")

    def test_anonuser_cannot_cancel_project(self):
        """An anonmous user cannot access the cancel project url and should be
        re-directed to login-page.

        """
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.cancelled)

        response = self.client.get(
            reverse("uncancel_project", kwargs={"slug": self.project.slug}), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.cancelled)
        self.assertEqual(self.project.status, "cancelled")

    def tearDown(self):
        self.project.delete()
        self.user1.delete()
        self.user.delete()


class TestDetailPageCancelledProjects(TestCase):
    """there are a number of requirements associated with cancelled projects:

    + a canceled project will have a warning on its detail page
    + a project must be approved to be canceled (un-approved projects will not display cancel button)
    + the cancel button on will not render when regular user sees page
    + the cancel button will be disabled if the project is already cancelled.
    """

    def setUp(self):
        # USERS
        self.user1 = UserFactory.create(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.user2 = UserFactory.create(
            username="bgumble", first_name="Barney", last_name="Gumble"
        )

        self.ms1 = MilestoneFactory.create(
            label="Approved", protected=True, category="Core", order=1, report=False
        )

        self.project1 = ProjectFactory.create(
            prj_cd="LHA_IA12_111", prj_ldr=self.user1, owner=self.user1
        )

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project1, milestone=signoff)

        # Barney is the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user2.groups.add(managerGrp)
        EmployeeFactory(user=self.user2, role="manager")

        self.message = "This project was cancelled."

        self.ApproveBtn = (
            '<button type="button" ' + 'class="btn btn-primary mx-1">Approve</button>'
        )

        self.CancelBtn = (
            '<button type="button" ' + 'class="btn btn-danger mx-1">Cancel Project</button>'
        )

        self.UnCancelBtn = (
            '<button type="button" ' + 'class="btn btn-danger mx-1">Un-Cancel</button>'
        )

    def test_no_cancel_btn_unapproved_projects(self):
        """If the manager views an un-approved project, there will not be a
        cancelled button or cancelled notification.

        """

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # the project is neither approved or canceled:
        self.assertFalse(self.project1.is_approved())
        self.assertFalse(self.project1.cancelled)

        # we should be able to approve it, but can't cancel it yet
        self.assertContains(response, self.ApproveBtn)
        self.assertNotContains(response, self.CancelBtn)
        self.assertNotContains(response, self.UnCancelBtn)
        self.assertNotContains(response, "Unapprove")
        self.assertNotContains(response, self.message)

    def test_cancel_btn_approved_projects(self):
        """When A manager views the detail of an approved project, the page
        should not contain a 'Approve' or 'UnApprove' button but
        should contain a Cancel button.  no warning message should
        appear.

        """
        self.project1.approve()

        # the project should now be approved (but not cancelled yet)
        self.assertTrue(self.project1.is_approved())
        self.assertFalse(self.project1.cancelled)

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertNotContains(response, self.ApproveBtn)
        self.assertContains(response, self.CancelBtn)
        self.assertNotContains(response, self.UnCancelBtn)
        self.assertNotContains(response, "Unapprove")
        self.assertNotContains(response, self.message)

    def test_notice_and_disabled_cancel_btn_cancelled_projects(self):
        """When A manager views the detail of a cancelled project, the page
        should contain a warning message and the cancel button should
        be disabled.
        """

        self.project1.approve()
        self.project1.cancelled = True
        self.project1.save()

        # the project should now be approved (but not cancelled yet)
        self.assertTrue(self.project1.is_approved())
        self.assertTrue(self.project1.cancelled)

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertNotContains(response, self.ApproveBtn)
        self.assertNotContains(response, self.CancelBtn)
        self.assertContains(response, self.UnCancelBtn)
        self.assertNotContains(response, "Unapprove")
        self.assertContains(response, self.message)

    def test_no_cancel_btn_regular_user(self):
        """If a regular user views an approved project page, that has not been
        cancelled, they will not see the cancel project button or the
        message.  The button should only be available to managers.
        """

        self.project1.approve()

        # the project should now be approved (but not cancelled yet)
        self.assertTrue(self.project1.is_approved())
        self.assertFalse(self.project1.cancelled)

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # it should not contain any buttons or cancelled messages:
        self.assertNotContains(response, self.ApproveBtn)
        self.assertNotContains(response, self.CancelBtn)
        self.assertNotContains(response, self.UnCancelBtn)
        self.assertNotContains(response, "Unapprove")
        self.assertNotContains(response, self.message)

    def test_cancel_message_regular_user(self):
        """If a regular user views the detail page for a project that was
        cancelled, the page will include an appropriate message.
        """

        self.project1.approve()
        self.project1.cancelled = True
        self.project1.save()

        # the project should now be approved (but not cancelled yet)
        self.assertTrue(self.project1.is_approved())
        self.assertTrue(self.project1.cancelled)

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # it should not contain any buttons:
        self.assertNotContains(response, self.ApproveBtn)
        self.assertNotContains(response, self.CancelBtn)
        self.assertNotContains(response, self.UnCancelBtn)
        self.assertNotContains(response, "Unapprove")
        # it should contain basic message:
        self.assertContains(response, self.message)


class ReOpenProjectTestCase(TestCase):
    """Verify that a manager can reopen a completed project, but regular
    and anonmous users cannot.."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(
            username="gcostansa", first_name="George", last_name="Costansa"
        )

        self.user1 = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # make george the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user.groups.add(managerGrp)
        EmployeeFactory(user=self.user, role="manager")

        self.signoff = MilestoneFactory.create(
            label="Sign Off", protected=True, category="Core", order=99, report=False
        )

        # now create a project using a different user
        self.owner = UserFactory()
        self.project = ProjectFactory(owner=self.owner)

        pms = ProjectMilestones.objects.get(
            project=self.project, milestone=self.signoff
        )
        pms.completed = datetime.now(pytz.utc)
        pms.save()

    def test_manager_reopens_nonproject_returns_404(self):
        """If a manager tries to access the url for project that does not
        exist, the response should be a 404.
        """

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("reopen_project", kwargs={"slug": "LHA_IA13_999"}), follow=True
        )
        self.assertEqual(response.status_code, 404)

    def test_manager_can_reopen_project(self):
        """A manager should be able to access the reopen project url and
        successfully reopen a project.
        """

        # make sure the project is complete to start with
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.is_complete())

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("reopen_project", kwargs={"slug": self.project.slug}), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")
        # it should be active:
        proj = Project.objects.get(slug=self.project.slug)
        self.assertFalse(proj.is_complete())

        # verify that the projectmilestone was created and has been populated
        pms = ProjectMilestones.objects.get(
            project=self.project, milestone=self.signoff
        )

        # the completed attr of our project milestone should be empty
        self.assertTrue(pms.completed is None)

    def test_user_cannot_reopen_project(self):
        """A regular user cannot access the reopen project url and should be
        re-directed to project detail page.

        """
        # make sure the project complete to start with

        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.is_complete())

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("reopen_project", kwargs={"slug": self.project.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # it still should be complete :
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.is_complete())

    def test_anonuser_cannot_reopen_project(self):
        """An anonmous user cannot access the reopen project url and should be
        re-directed to login-page.

        """

        # login = self.client.login(username=self.user1.username,
        #                          password='Abcd1234')
        # self.assertTrue(login)
        response = self.client.get(
            reverse("reopen_project", kwargs={"slug": self.project.slug}), follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        # it still should still be complete:
        proj = Project.objects.get(slug=self.project.slug)
        self.assertTrue(proj.is_complete())

    def tearDown(self):
        self.project.delete()
        self.user1.delete()
        self.user.delete()


class TestProjectFundingProjectDetail(TestCase):
    """The project detail page will contain (or not contain) elements
    assocaited with funding depending on whether or not there is fundind
    associated with a project and if there are more than one funding
    source.

    """

    def setUp(self):

        self.project0 = ProjectFactory.create(prj_cd="LHA_IA99_000")
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA99_111")
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA99_222")

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project0, milestone=signoff)
        ProjectMilestonesFactory(project=self.project1, milestone=signoff)
        ProjectMilestonesFactory(project=self.project2, milestone=signoff)

        self.source1 = FundingSourceFactory.create(abbrev="spa")
        self.source2 = FundingSourceFactory.create(name="COA", abbrev="coa")

        self.projectfunding1 = ProjectFundingFactory.create(
            project=self.project1, source=self.source1, odoe=1500, salary=5000
        )

        self.projectfunding2 = ProjectFundingFactory.create(
            project=self.project2, source=self.source1, odoe=1500, salary=5000
        )

        self.projectfunding3 = ProjectFundingFactory.create(
            project=self.project2, source=self.source2, odoe=2000, salary=8000
        )

    def test_project_detail_no_funding_provided(self):
        """If whe access the details page for a project which does not report
        any associted funding, the panel containing the funding information
        should not be rendered."""

        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project0.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertNotContains(response, "Funding")
        self.assertNotContains(response, "Salary")
        self.assertNotContains(response, "ODOE")

    def test_project_detail_one_funding_source(self):
        """If we access the detail page for a project with one funding source,
        the response should contain the strings 'Funding', 'Salary'
        and 'ODOE' and a comma formatted numbers for these values and
        their total, as well as the abbreviation of the funding source."""

        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertContains(response, "Funding")
        self.assertContains(response, "Salary")
        self.assertContains(response, "ODOE")
        self.assertContains(response, "spa")
        self.assertContains(response, "1,500")
        self.assertContains(response, "5,000")
        self.assertContains(response, "6,500")

    def test_project_detail_several_funding_sources(self):
        """If we access the details view a project with two or more funding
        sources, the response should contains the strings 'Funding',
        'Salary' and 'ODOE', comma formatted numbers for these values
        for each of the sources and their totals, a totals lines
        summarizing the total salary, total odoe and grand total for
        the project.  The abbreviations for each of the funding
        sources should also be included.
        """

        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project2.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertContains(response, "Funding")
        self.assertContains(response, "Salary")
        self.assertContains(response, "ODOE")
        self.assertContains(response, "spa")
        self.assertContains(response, "1,500")
        self.assertContains(response, "5,000")
        self.assertContains(response, "6,500")

        self.assertContains(response, "spa")
        self.assertContains(response, "2,000")
        self.assertContains(response, "8,000")
        self.assertContains(response, "10,000")

        self.assertContains(response, "Total")
        self.assertContains(response, "3,500")
        self.assertContains(response, "13,000")
        self.assertContains(response, "16,500")

    def tearDown(self):
        pass


class TestDetailPageReOpenProject(TestCase):
    """When a project is completed, there are a number of items that
    should not appear on the page regardless of whether or not the
    user is a manager or not.  If the project is complete, and a
    manager access the page, a 'Re-open button should appear'
    """

    def setUp(self):
        # USERS
        self.user1 = UserFactory.create(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.user2 = UserFactory.create(
            username="bgumble", first_name="Barney", last_name="Gumble"
        )

        self.project1 = ProjectFactory.create(
            prj_cd="LHA_IA12_111", prj_ldr=self.user1, owner=self.user1
        )

        self.signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project1, milestone=self.signoff)

        # Barney is the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user2.groups.add(managerGrp)
        EmployeeFactory(user=self.user2, role="manager")

        self.EditBtn = (
            '<button type="button" '
            + 'class="btn btn-outline-secondary text-dark mx-1">Edit Information</button>'
        )

        self.SignOffBtn = (
            '<button type="button" ' + 'class="btn btn-success mx-1">Sign Off</button>'
        )

        self.ReOpenBtn = (
            '<button type="button" '
            + 'class="btn btn-success mx-1">Re-Open Project</button>'
        )

    def test_no_reopen_btn_active_project_manager(self):

        """If the manager views an active project, there will not be a re-open
        project button, but there will be buttons to edit, sign-off
        and cancel project.

        """

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # the project is neither approved or canceled:
        self.assertFalse(self.project1.is_complete())

        # we should be able to edit, sign off this project but
        # shouldn't be able to re-open it
        self.assertContains(response, self.EditBtn)
        self.assertContains(response, self.SignOffBtn)
        self.assertNotContains(response, self.ReOpenBtn)

    def test_reopen_btn_completed_project_manager(self):
        """If the manager views an completed project, there will be a re-open
        project button, and the buttons to edit, sign-off and cancel
        project. will not be included in the response.
        """

        pms = ProjectMilestones.objects.get(
            project=self.project1, milestone=self.signoff
        )
        pms.completed = datetime.now(pytz.utc)
        pms.save()

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # the project is neither approved or canceled:
        self.assertTrue(self.project1.is_complete())

        # We should no longer have buttons ot edit or sign off on our
        # project, but we should be able to re-open it.
        self.assertNotContains(response, self.EditBtn)
        self.assertNotContains(response, self.SignOffBtn)
        self.assertContains(response, self.ReOpenBtn)

    def test_no_reopen_btn_completed_project_user(self):
        """If the a logged in user views a completed project, there
        will not be buttons to to edit, sign-off, cancel or re-open
        the project."""

        pms = ProjectMilestones.objects.get(
            project=self.project1, milestone=self.signoff
        )
        pms.completed = datetime.now(pytz.utc)
        pms.save()

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # this project is still complete, so is_complete() will be True
        self.assertTrue(self.project1.is_complete())

        # We should no longer have buttons to edit, or sign off, or
        # re-open our project
        self.assertNotContains(response, self.EditBtn)
        self.assertNotContains(response, self.SignOffBtn)
        self.assertNotContains(response, self.ReOpenBtn)

    def test_no_reopen_btn_active_project_user(self):
        """If the a logged in user views an active project, there will be
        buttons to to edit it, but they should not be able to
        sign-off, cancel, or re-open the project.
        """

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project1.slug}), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # this project is still active, so is_complete() will be False
        self.assertFalse(self.project1.is_complete())

        # We should have an edit button (as this project is open and
        # homer is the project owner), but we should not be able to
        # sign-off or re-open it.
        self.assertContains(response, self.EditBtn)
        self.assertNotContains(response, self.SignOffBtn)
        self.assertNotContains(response, self.ReOpenBtn)


class ProjectDetailManagerTestCase(TestCase):
    """verify that a manager can see a project and be able to both
    edit the record and update milestones."""

    def setUp(self):
        self.client = Client()
        self.user = UserFactory(
            username="gcostansa", first_name="George", last_name="Costansa"
        )
        # make george the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user.groups.add(managerGrp)
        EmployeeFactory(user=self.user, role="manager")

        # now create a project using a different user
        self.owner = UserFactory()
        self.project = ProjectFactory(owner=self.owner)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project, milestone=signoff)

    def test_with_Login(self):
        """if we login with a valid user, we will be allowed to view
        the page"""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(
            reverse("project_detail", kwargs={"slug": self.project.slug})
        )
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")
        # self.assertContains(response, 'Project Detail')
        self.assertContains(response, self.project.prj_cd)
        self.assertContains(response, self.project.prj_nm)
        prj_ldr = "{0} {1}".format(
            self.project.prj_ldr.first_name, self.project.prj_ldr.last_name
        )
        self.assertContains(response, prj_ldr)
        self.assertContains(response, "Milestones")
        self.assertContains(response, "Reporting Requirements")

        # a manager should be able to both edit the project and adjust
        # milestones accordingly.
        self.assertTrue(response.context["edit"])
        self.assertTrue(response.context["manager"])

    def tearDown(self):
        self.project.delete()
        self.owner.delete()
        self.user.delete()


# ================================
# APPROVED PROJECT LIST


class ApprovedProjectListUserTestCase(TestCase):
    """All logged users should be able to see the list of approved
    projects, but only managers can makes updates to the list"""

    def setUp(self):
        # create two projects, one that will be approved, and one that
        # isn't.  Only the approved one should appear in the list.
        self.client = Client()
        self.user = UserFactory()
        self.employee = EmployeeFactory(user=self.user)

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        self.project = ProjectFactory(owner=self.user)

        self.project2 = ProjectFactory(
            prj_cd="LHA_IA12_111",
            prj_nm="An approved project",
            prj_ldr=self.user,
            owner=self.user,
        )
        self.project2.approve()
        # self.project2.save()

    def test_with_Login(self):
        """if we login with a valid user, we will be allowed to view
        the page"""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ApprovedProjectsList"))
        self.assertEqual(response.status_code, 200)

        # self.assertTemplateUsed(response, 'pjtk2/ApprovedProjectList.html')
        self.assertTemplateUsed(response, "pjtk2/ProjectList.html")
        self.assertContains(response, "Projects")
        # it should not contain the project that isn't approved
        self.assertNotContains(response, self.project.prj_cd)
        self.assertNotContains(response, self.project.prj_nm)

        # this one is approved and should be in the list
        self.assertContains(response, self.project2.prj_cd)
        self.assertContains(response, self.project2.prj_nm)

        # since this user is not a manager, she should not be able to
        # update the list
        self.assertNotContains(response, "Update this list")

    def test_without_Login(self):
        """if we try to view page without logging in, we should be
        re-directed to the login page"""

        response = self.client.get(reverse("ApprovedProjectsList"))
        self.assertEqual(response.status_code, 302)
        redirectstring = "%s?next=%s" % (
            reverse("login"),
            reverse("ApprovedProjectsList"),
        )
        self.assertRedirects(response, redirectstring)

    def tearDown(self):
        self.project.delete()
        self.user.delete()


class ApprovedProjectListManagerTestCase(TestCase):
    """Managers should  be able to see the list of approved
    projects, and see the link to update the list"""

    def setUp(self):
        # create two projects, one that will be approved, and one that
        # isn't.  Only the approved one should appear in the list.
        self.client = Client()
        self.owner = UserFactory()

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        self.project = ProjectFactory(owner=self.owner)

        self.project2 = ProjectFactory(
            prj_cd="LHA_IA12_111",
            prj_nm="An approved project",
            prj_ldr=self.owner,
            owner=self.owner,
        )
        # self.project2.Approved = True
        self.project2.save()
        self.project2.approve()

        # create a differnt user that will be the manager
        self.user = UserFactory(
            username="gconstansa", first_name="George", last_name="Costansa"
        )
        # make george the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user.groups.add(managerGrp)
        EmployeeFactory(user=self.user, role="manager")

    def test_with_Login(self):
        """if we login with a valid user, we will be allowed to view
        the page"""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ApprovedProjectsList"))
        self.assertEqual(response.status_code, 200)

        # self.assertTemplateUsed(response, 'pjtk2/ApprovedProjectList.html')
        self.assertTemplateUsed(response, "pjtk2/ProjectList.html")
        self.assertContains(response, "Projects")
        # it should not contain the project that isn't approved
        self.assertNotContains(response, self.project.prj_cd)
        self.assertNotContains(response, self.project.prj_nm)

        # this one is approved and should be in the list
        self.assertContains(response, self.project2.prj_cd)
        self.assertContains(response, self.project2.prj_nm)

        # since this user is a manager, she should be able to
        # update the list
        self.assertContains(response, "Update this list")

    def test_without_Login(self):
        """if we try to view page without logging in, we should be
        re-directed to the login page"""

        response = self.client.get(reverse("ApprovedProjectsList"))
        self.assertEqual(response.status_code, 302)
        redirectstring = "%s?next=%s" % (
            reverse("login"),
            reverse("ApprovedProjectsList"),
        )
        self.assertRedirects(response, redirectstring)

    def tearDown(self):
        self.project.delete()
        self.user.delete()


# ================================
# APPROVE PROJECTS


class ApproveUnapproveProjectsTestCase(TestCase):
    """Verify that a manager can approve and unapprove projects"""

    def setUp(self):
        """ """
        # USER
        self.user1 = UserFactory.create(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.user2 = UserFactory.create(
            username="mburns", first_name="Burns", last_name="Montgomery"
        )
        # make Mr. Burns the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user2.groups.add(managerGrp)
        EmployeeFactory(user=self.user2, role="manager")

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        # we need to create some models with different years - starting
        # with the current year (the actual model objects use the real
        # current year so the project codes must be dynamically built
        # to ensure the tests pass in the future).
        self.year = datetime.now().year

        # Two projects from this year:
        prj_cd = "LHA_IA%s_111" % str(self.year)[-2:]
        self.project1 = ProjectFactory.create(
            prj_cd=prj_cd, prj_ldr=self.user1, owner=self.user1
        )

        prj_cd = "LHA_IA%s_222" % str(self.year)[-2:]
        self.project2 = ProjectFactory.create(
            prj_cd=prj_cd, prj_ldr=self.user1, owner=self.user1
        )
        # Two projects from last year:
        prj_cd = "LHA_IA%s_333" % str(self.year - 1)[-2:]
        self.project3 = ProjectFactory.create(
            prj_cd=prj_cd, prj_ldr=self.user1, owner=self.user1
        )

        prj_cd = "LHA_IA%s_444" % str(self.year - 1)[-2:]
        self.project4 = ProjectFactory.create(
            prj_cd=prj_cd, prj_ldr=self.user1, owner=self.user1
        )

        # one project from 3 years ago
        prj_cd = "LHA_IA%s_555" % str(self.year - 3)[-2:]
        self.project5 = ProjectFactory.create(
            prj_cd=prj_cd, prj_ldr=self.user1, owner=self.user1
        )

        # One project for next year (submitted by a keener):
        prj_cd = "LHA_IA%s_666" % str(self.year + 1)[-2:]
        self.project6 = ProjectFactory.create(
            prj_cd=prj_cd, prj_ldr=self.user1, owner=self.user1
        )

        # approve all of the projects
        self.project1.approve()
        self.project2.approve()
        self.project3.approve()
        self.project4.approve()
        self.project5.approve()
        self.project6.approve()

    def test_without_Login(self):
        """if we try to view page without logging in, we should be
        re-directed to the login page"""

        response = self.client.get(reverse("ApproveProjects"))
        self.assertEqual(response.status_code, 302)

        redirectstring = "%s?next=%s" % (reverse("login"), reverse("ApproveProjects"))
        self.assertRedirects(response, redirectstring)

    def test_that_nonmanagers_are_redirected(self):
        """only managers can approve/unapprove projects.  Verify that
        homer is redirected to the approved project list if he tries
        to log in to the approved projects view."""

        login = self.client.login(username=self.user1.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ApproveProjects"), follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ApprovedProjectList.html")
        self.assertContains(response, "Approved Projects")
        self.assertNotContains(response, "This Year")
        self.assertNotContains(response, "Last Year")

    def test_that_only_managers_can_login(self):
        """verify that Mr Burns is able to successful view the form"""

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ApproveProjects"), follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ApproveProjects.html")
        self.assertContains(response, "This Year")
        self.assertContains(response, "Last Year")

    def test_that_form_renders_properly(self):
        """Verify that when Mr. Burns view the form, it contains
        appropriate entries for both this year and last year.  This
        year should contain one entry for a future project year.
        Projects more than one year old should not appear on the form.
        the project codes should also appear as link to their
        respective detail pages."""

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ApproveProjects"), follow=True)

        # This year
        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project1.slug,)),
            self.project1.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project2.slug,)),
            self.project2.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

        # last year

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project3.slug,)),
            self.project3.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project4.slug,)),
            self.project4.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

        # the old project should NOT be listed in any form in the response
        self.assertNotContains(response, self.project5.prj_cd)
        # the project from the future
        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project6.slug,)),
            self.project6.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

    def test_projects_for_thisyear_can_be_approved(self):
        """by default projects should not be approved.  Verify that
        Mr. Burns can login and successfully approve two from the
        current year."""

        # by default, the projects are all approved we need to
        # unapproved them before we run this test
        self.project1.unapprove()
        self.project2.unapprove()
        self.project3.unapprove()
        self.project4.unapprove()
        self.project5.unapprove()
        self.project6.unapprove()

        # check that our update worked:
        projects = Project.this_year.all()
        self.assertQuerysetEqual(
            projects, [False, False, False], lambda a: a.is_approved()
        )

        # now login and make the changes
        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)

        form_data = {
            "thisyear-TOTAL_FORMS": 3,
            "thisyear-INITIAL_FORMS": 3,
            "form-type": "thisyear",
            "thisyear-0-id": str(self.project6.id),
            "thisyear-0-prj_ldr": str(self.project6.prj_ldr.id),
            "thisyear-0-Approved": True,
            "thisyear-1-id": str(self.project1.id),
            "thisyear-1-prj_ldr": str(self.project1.prj_ldr.id),
            "thisyear-1-Approved": True,
            "thisyear-2-id": str(self.project2.id),
            "thisyear-2-prj_ldr": str(self.project2.prj_ldr.id),
            "thisyear-2-Approved": True,
        }

        # submit the form
        response = self.client.post(reverse("ApproveProjects"), form_data)

        # they should all be false now:
        thisyear = Project.this_year.all()
        self.assertEqual(thisyear.count(), 3)
        self.assertQuerysetEqual(
            thisyear, [True, True, True], lambda a: a.is_approved()
        )

    def test_projects_for_thisyear_can_be_unapproved(self):
        """Oops - funding was cut.  A project from this year that was
        approved must be unapproved."""

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)

        # verify database settings before submitting form
        thisyear = Project.this_year.all()
        self.assertEqual(thisyear.count(), 3)
        self.assertQuerysetEqual(
            thisyear, [True, True, True], lambda a: a.is_approved()
        )

        form_data = {
            "thisyear-TOTAL_FORMS": 3,
            "thisyear-INITIAL_FORMS": 3,
            "form-type": "thisyear",
            "thisyear-0-id": str(self.project6.id),
            "thisyear-0-prj_ldr": str(self.project6.prj_ldr.id),
            "thisyear-0-Approved": False,
            "thisyear-1-id": str(self.project1.id),
            "thisyear-1-prj_ldr": str(self.project1.prj_ldr.id),
            "thisyear-1-Approved": False,
            "thisyear-2-id": str(self.project2.id),
            "thisyear-2-Approved": False,
            "thisyear-2-prj_ldr": str(self.project2.prj_ldr.id),
        }

        # submit the form
        response = self.client.post(reverse("ApproveProjects"), form_data, follow=True)

        # they should all be false now:
        thisyear = Project.this_year.all()

        self.assertEqual(thisyear.count(), 3)
        self.assertQuerysetEqual(
            thisyear, [False, False, False], lambda a: a.is_approved()
        )

        # lets make sure that we can submit with both true and false values:
        form_data = {
            "thisyear-TOTAL_FORMS": 3,
            "thisyear-INITIAL_FORMS": 3,
            "form-type": "thisyear",
            "thisyear-0-id": str(self.project6.id),
            "thisyear-0-prj_ldr": str(self.project6.prj_ldr.id),
            "thisyear-0-Approved": False,
            "thisyear-1-id": str(self.project1.id),
            "thisyear-1-prj_ldr": str(self.project1.prj_ldr.id),
            "thisyear-1-Approved": True,
            "thisyear-2-id": str(self.project2.id),
            "thisyear-2-prj_ldr": str(self.project2.prj_ldr.id),
            "thisyear-2-Approved": False,
        }

        # submit the form
        response = self.client.post(reverse("ApproveProjects"), form_data)

        # they should all be false now:
        thisyear = Project.this_year.all()
        self.assertEqual(thisyear.count(), 3)
        self.assertQuerysetEqual(
            thisyear, [False, True, False], lambda a: a.is_approved(), ordered=False
        )

    def test_projects_for_lastyear_can_be_approved(self):
        """by default projects should not be approved.  Verify that
        Mr. Burns can login and successfully approve a project from last year
        that he forgot to approve then."""

        # by default, the projects are all approved we need to
        # unapproved them before we run this test
        self.project1.unapprove()
        self.project2.unapprove()
        self.project3.unapprove()
        self.project4.unapprove()
        self.project5.unapprove()
        self.project6.unapprove()

        # check that our update worked:
        projects = Project.last_year.all()
        self.assertQuerysetEqual(projects, [False, False], lambda a: a.is_approved())

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)

        # verify database settings before submitting form
        lastyear = Project.last_year.all()
        self.assertEqual(lastyear.count(), 2)
        self.assertQuerysetEqual(lastyear, [False, False], lambda a: a.is_approved())

        form_data = {
            "lastyear-TOTAL_FORMS": 2,
            "lastyear-INITIAL_FORMS": 2,
            "form-type": "lastyear",
            "lastyear-0-id": str(self.project3.id),
            "lastyear-0-prj_ldr": str(self.project3.prj_ldr.id),
            "lastyear-0-Approved": True,
            "lastyear-1-id": str(self.project4.id),
            "lastyear-1-prj_ldr": str(self.project4.prj_ldr.id),
            "lastyear-1-Approved": True,
        }

        # submit the form
        response = self.client.post(reverse("ApproveProjects"), form_data, follow=True)

        # they should all be false now:
        lastyear = Project.last_year.all()
        self.assertEqual(lastyear.count(), 2)
        project_ids = [x.id for x in lastyear]
        self.assertIn(self.project3.id, project_ids)
        self.assertIn(self.project4.id, project_ids)
        self.assertQuerysetEqual(lastyear, [True, True], lambda a: a.is_approved())

    def test_projects_for_lastyear_can_be_unapproved(self):
        """Verify that Mr. Burns can login and successfully un-approve a
        project from last year that was accidentally approved."""

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)

        # verify database settings before submitting form
        lastyear = Project.last_year.all()
        self.assertEqual(lastyear.count(), 2)
        self.assertQuerysetEqual(lastyear, [True, True], lambda a: a.is_approved())

        form_data = {
            "lastyear-TOTAL_FORMS": 2,
            "lastyear-INITIAL_FORMS": 2,
            "form-type": "lastyear",
            "lastyear-0-id": str(self.project3.id),
            "lastyear-0-prj_ldr": str(self.project3.prj_ldr.id),
            "lastyear-0-Approved": False,
            "lastyear-1-id": str(self.project4.id),
            "lastyear-1-prj_ldr": str(self.project4.prj_ldr.id),
            "lastyear-1-Approved": False,
        }

        # submit the form
        response = self.client.post(reverse("ApproveProjects"), form_data)

        # they should all be false now:
        lastyear = Project.last_year.all()
        self.assertEqual(lastyear.count(), 2)
        self.assertQuerysetEqual(lastyear, [False, False], lambda a: a.is_approved())

        # lets make sure that we can submit with both true and false values:
        form_data = {
            "lastyear-TOTAL_FORMS": 2,
            "lastyear-INITIAL_FORMS": 2,
            "form-type": "lastyear",
            "lastyear-0-id": str(self.project3.id),
            "lastyear-0-prj_ldr": str(self.project3.prj_ldr.id),
            "lastyear-0-Approved": False,
            "lastyear-1-id": str(self.project4.id),
            "lastyear-1-prj_ldr": str(self.project4.prj_ldr.id),
            "lastyear-1-Approved": True,
        }

        # submit the form
        response = self.client.post(reverse("ApproveProjects"), form_data)

        # they should all be false now:
        lastyear = Project.last_year.all()
        self.assertEqual(lastyear.count(), 2)
        self.assertQuerysetEqual(
            lastyear, [False, True], lambda a: a.is_approved(), ordered=False
        )

    def tearDown(self):

        self.project6.delete()
        self.project5.delete()
        self.project4.delete()
        self.project3.delete()
        self.project2.delete()
        self.project1.delete()
        self.user1.delete()
        self.user2.delete()


class ApproveProjectsEmptyTestCase(TestCase):
    """Verify that a meaningful message is displayed if there aren't
    any projects waiting to be approved."""

    def setUp(self):

        self.user = UserFactory.create(
            username="mburns", first_name="Burns", last_name="Montgomery"
        )
        # make Mr. Burns the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user.groups.add(managerGrp)
        EmployeeFactory(user=self.user, role="manager")
        self.year = datetime.now().year

    def test_with_Login(self):
        """if we login with as a manager, we will be allowed to view
        the page, but it should give us a pleasant notice that no
        projects are pending our approval
        ."""
        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        response = self.client.get(reverse("ApproveProjects"))
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, "pjtk2/ApproveProjects.html")
        self.assertContains(response, "Approve Projects")
        # this year
        msg = "There are currently no projects for %s" % self.year
        self.assertContains(response, msg)
        # last year
        msg = "There are currently no projects for %s" % str(self.year - 1)
        self.assertContains(response, msg)

    def tearDown(self):
        self.user.delete()


class ChangeReportingRequirementsTestCase2(TestCase):
    """This class verifies that new reporting requirements can be
    added through the report update form.  This report was originally
    attempted using webtest in views2_test.py.  I was unable to get
    webtest to submit the second "NewReport" form properly."""

    def setUp(self):

        # USER
        self.user2 = UserFactory.create(
            username="mburns", first_name="Burns", last_name="Montgomery"
        )
        # make Mr. Burns the manager:
        # managerGrp, created = Group.objects.get_or_create(name="manager")
        # self.user2.groups.add(managerGrp)
        EmployeeFactory(user=self.user2, role="manager")

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        self.rep4 = MilestoneFactory.create(
            label="Budget Report", category="Custom", order=99, report=True
        )
        self.rep5 = MilestoneFactory.create(
            label="Creel Summary Statistics", category="Custom", order=99, report=True
        )

        # PROJECTS
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user2)

    def test_Add_New_Report2(self):
        """verify that we can add new report reporting requirements
        using the second form on the UpdateReporting form."""

        login = self.client.login(username=self.user2.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("Reports", args=(self.project1.slug,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/reportform.html")
        self.assertContains(response, "Core Reporting Requirements")
        self.assertContains(response, "Additional Reporting Requirements")

        resp = self.client.post(url, {"new_report": "COA Summary"})
        self.assertEqual(resp.status_code, 302)

        reports = Milestone.objects.filter(category="Custom")
        self.assertEqual(reports.count(), 3)
        self.assertEqual(reports.filter(label="Coa Summary").count(), 1)

    def tearDown(self):

        self.project1.delete()
        self.rep5.delete()
        self.rep4.delete()
        self.user2.delete()


class TestTagListView(TestCase):
    """associate some tags with some projects and verify that they
    appear in the tags list
    """

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222", owner=self.user)

        self.project1.tags.add("perch", "walleye", "whitefish")
        self.project1.tags.add("perch", "carp")

    def test_tag_list(self):
        """verify that we can add and remove tags to a project"""

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)

        url = reverse("project_tag_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/project_tag_list.html")
        self.assertContains(response, "Keywords associated with one or more projects:")

        self.assertContains(response, "perch")
        self.assertContains(response, "walleye")
        self.assertContains(response, "whitefish")
        self.assertContains(response, "carp")


class ProjectQuickSearch(TestCase):
    """The project quick search in the nav bar should return a list of
    project that contain 'q' in their project code.
    """

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222", owner=self.user)
        self.project3 = ProjectFactory.create(prj_cd="LHA_IA00_000", owner=self.user)

    def test_project_quick_search_all(self):
        """a quick search pattern that matches all of our projects"""

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)

        url = reverse("project_search")
        response = self.client.get(url, {"prj_cd__like": "LHA"})
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectListSimple.html")

        link_base = '<a href="{0}">{1}</a>'
        linkstring = link_base.format(
            reverse("project_detail", args=(self.project1.slug,)), self.project1.prj_cd
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = link_base.format(
            reverse("project_detail", args=(self.project2.slug,)), self.project2.prj_cd
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = link_base.format(
            reverse("project_detail", args=(self.project3.slug,)), self.project3.prj_cd
        )
        self.assertContains(response, linkstring, html=True)

    def test_project_quick_search_all_case_insensitive(self):
        """a quick search pattern that matches all of our projects but
        was submitted in lower case.  All three projects should still
        be returned.
        """

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)

        url = reverse("project_search")
        response = self.client.get(url, {"prj_cd__like": "lha"})
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectListSimple.html")

        link_base = '<a href="{0}">{1}</a>'
        linkstring = link_base.format(
            reverse("project_detail", args=(self.project1.slug,)), self.project1.prj_cd
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = link_base.format(
            reverse("project_detail", args=(self.project2.slug,)), self.project2.prj_cd
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = link_base.format(
            reverse("project_detail", args=(self.project3.slug,)), self.project3.prj_cd
        )
        self.assertContains(response, linkstring, html=True)

    def test_project_quick_search_no_match(self):
        """If no matches where found, the repsonse should
        state:"Sorry, no projects match that criteria."

        """

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)

        url = reverse("project_search")
        response = self.client.get(url, {"prj_cd": "foobar"})
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectListSimple.html")
        self.assertContains(response, "Sorry, no projects match that criteria.")

    def test_project_quick_search_one_match(self):
        """a quick search pattern that matches just one of our
        projects.  It should be the only one in the response.
        """

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)

        url = reverse("project_search")
        response = self.client.get(url, {"prj_cd__like": "000"})
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectListSimple.html")

        link_base = '<a href="{0}">{1}</a>'
        linkstring = link_base.format(
            reverse("project_detail", args=(self.project1.slug,)), self.project1.prj_cd
        )
        self.assertNotContains(response, linkstring, html=True)

        linkstring = link_base.format(
            reverse("project_detail", args=(self.project2.slug,)), self.project2.prj_cd
        )
        self.assertNotContains(response, linkstring, html=True)

        # this one should be there
        linkstring = link_base.format(
            reverse("project_detail", args=(self.project3.slug,)), self.project3.prj_cd
        )
        self.assertContains(response, linkstring, html=True)


class UserProjectList(TestCase):
    """The user proejct list should return all of the projects assocaited
    with a user, including those projects in which they were either
    the proejct lead or field lead.

    """

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.client = Client()

        self.user1 = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.user2 = UserFactory(
            username="mburns", first_name="Monty", last_name="Burns"
        )

        self.user3 = UserFactory(
            username="bgumble", first_name="Barney", last_name="Gumble"
        )

        self.project1 = ProjectFactory(
            prj_cd="LHA_IA12_111", prj_nm="First Fake Project", prj_ldr=self.user1
        )
        self.project2 = ProjectFactory(
            prj_cd="LHA_IA12_222",
            prj_nm="Second Fake Project",
            prj_ldr=self.user1,
            field_ldr=self.user2,
        )
        self.project3 = ProjectFactory(
            prj_cd="LHA_IA00_000",
            prj_nm="Third Fake Project",
            prj_ldr=self.user1,
            field_ldr=self.user1,
        )

    def test_prj_ldr(self):
        """Homer was involved in all three projects, if we navigate to his
        project we should see all three project codes.

        """

        url = reverse("user_project_list", kwargs={"username": self.user1.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectList.html")

        self.assertContains(
            response, "{0} {1}".format(self.user1.first_name, self.user1.last_name)
        )

        self.assertContains(response, self.project1.prj_cd)
        self.assertContains(response, self.project1.prj_nm)

        self.assertContains(response, self.project2.prj_cd)
        self.assertContains(response, self.project2.prj_nm)

        self.assertContains(response, self.project3.prj_cd)
        self.assertContains(response, self.project3.prj_nm)

    def test_field_ldr(self):
        """Mr. Burns was involved as field lead for only one project.  It is
        the only project code that should appear in his project list.

        """

        url = reverse("user_project_list", kwargs={"username": self.user2.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectList.html")

        self.assertContains(
            response, "{0} {1}".format(self.user2.first_name, self.user2.last_name)
        )

        #  NOT!!
        self.assertNotContains(response, self.project1.prj_cd)
        self.assertNotContains(response, self.project1.prj_nm)

        self.assertContains(response, self.project2.prj_cd)
        self.assertContains(response, self.project2.prj_nm)

        #  NOT!!
        self.assertNotContains(response, self.project3.prj_cd)
        self.assertNotContains(response, self.project3.prj_nm)

    def test_joe_user(self):
        """Barney Gumble was not involved in any of hte projects.  The project
        codes should not appear in his project list and an appropriate message
        should be displayed.

        """
        url = reverse("user_project_list", kwargs={"username": self.user3.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed("pjtk2/ProjectList.html")

        self.assertContains(
            response, "{0} {1}".format(self.user3.first_name, self.user3.last_name)
        )

        msg = "Sorry no projects available."
        self.assertContains(response, msg)

        #  NOT!!
        self.assertNotContains(response, self.project1.prj_cd)
        self.assertNotContains(response, self.project1.prj_nm)

        #  NOT!!
        self.assertNotContains(response, self.project2.prj_cd)
        self.assertNotContains(response, self.project2.prj_nm)

        #  NOT!!
        self.assertNotContains(response, self.project3.prj_cd)
        self.assertNotContains(response, self.project3.prj_nm)

    def tearDown(self):
        self.project3.delete()
        self.project2.delete()
        self.project1.delete()
        self.user3.delete()
        self.user2.delete()
        self.user1.delete()
