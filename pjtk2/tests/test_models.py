import datetime
import sys

import pytest
import pytz
from django.db.models.signals import post_save, pre_save
from django.test import TestCase
from pjtk2.models import (
    Bookmark,
    Family,
    Project,
    ProjectImage,
    ProjectMilestones,
    send_notice_prjms_changed,
)
from pjtk2.tests.factories import (
    EmployeeFactory,
    FundingSourceFactory,
    LakeFactory,
    MilestoneFactory,
    ProjectFactory,
    ProjectFundingFactory,
    ProjectMilestonesFactory,
    ProjProtocolFactory,
    ProjTypeFactory,
    ReportFactory,
    UserFactory,
)

from ..utils.helpers import get_minions, get_supervisors


@pytest.fixture(scope="module", autouse=True)
def disconnect_signals():
    """disconnect the signals before each test - not needed here"""
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)


def print_err(*args):
    sys.stderr.write(" ".join(map(str, args)) + "\n")


@pytest.mark.django_db
def test_project_image_str():
    """The string method of a project images should return the string
    representation of the project followed by the figure catption.

    'Fake Project (LHA_IA12_345) - My cool picture.'

    """

    prj_cd = "LHA_IA12_345"
    prj_nm = "Fake Project"
    figure_caption = "My cool picture."

    MilestoneFactory(label="Approved")
    project = ProjectFactory(prj_cd=prj_cd, prj_nm=prj_nm)
    image = ProjectImage(caption=figure_caption, project=project)
    shouldbe = "{} ({}) - {}".format(prj_nm, prj_cd, figure_caption)
    assert str(image) == shouldbe


class TestProjectApproveUnapproveMethods(TestCase):
    """Project instances have been given class methods to approve,
    rove and sign off.  These tests verify that they work as
    expected.
    """

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # Add milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Completed", category="Core", order=2, report=False
        )
        self.milestone3 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)

    def test_approve_unapprove_project(self):

        # verify that the project milestone for this project is null
        # before we call the method
        milestone = ProjectMilestones.objects.get(
            project=self.project1, milestone__label="Approved"
        )
        self.assertIsNone(milestone.completed)

        # call self.project1.approve()
        self.project1.approve()

        # assert that the value in completed is not null and that it is
        # close to the current time
        now = datetime.datetime.now(pytz.utc)
        milestone = ProjectMilestones.objects.get(
            project=self.project1, milestone__label="Approved"
        )
        completed = milestone.completed
        self.assertIsNotNone(completed)
        self.assertTrue((completed - now) < datetime.timedelta(seconds=1))

        # call self.project1.unapprove()
        self.project1.unapprove()
        # assert that the value in completed is null
        milestone = ProjectMilestones.objects.get(
            project=self.project1, milestone__label="Approved"
        )
        completed = milestone.completed
        self.assertIsNone(completed)

    def test_signoff_project(self):

        # verify that the 'Sign off' project milestone for this project is null
        # before we call the method

        # assert that the value in completed is not null and that it is
        # close to the current time

        milestone = ProjectMilestones.objects.get(
            project=self.project1, milestone__label="Sign off"
        )
        self.assertIsNone(milestone.completed)

        # call self.project1.approve()
        # call self.project1.signoff()
        self.project1.signoff(self.user)

        # assert that the value in completed is not null and that it is
        # close to the current time
        now = datetime.datetime.now(pytz.utc)
        milestone = ProjectMilestones.objects.get(
            project=self.project1, milestone__label="Sign off"
        )
        completed = milestone.completed
        self.assertIsNotNone(completed)
        self.assertTrue((completed - now) < datetime.timedelta(seconds=1))

    def test_reopen_project(self):

        # verify that the 'reopen' method removed the date from the
        # sign-off milestone associated with this project.

        milestone = ProjectMilestones.objects.get(
            project=self.project1, milestone__label="Sign off"
        )
        milestone.completed = datetime.datetime.now(pytz.utc)

        milestone.save()

        # verfify that the poject is currently complete
        self.assertTrue(self.project1.is_complete())
        # re-open the project
        self.project1.reopen()
        # verify that it so not longer considered complete.
        self.assertFalse(self.project1.is_complete())

    def tearDown(self):

        self.project1.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.milestone3.delete()
        self.user.delete()


class TestProjectModel(TestCase):
    def setUp(self):

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # self.employee = EmployeeFactory(user=self.user)
        MilestoneFactory(label="Approved")
        # define these as strings here so that we can access them later
        # and verify that the returned values match.
        self.commentStr = "This is a fake comment."
        self.abstractStr = "This is a fake abstract."
        self.ProjectName = "Homer's Odyssey"

        # we need to create some models with different years - starting
        # with the current year.
        yr = datetime.datetime.now()
        prj_cd = "LHA_IA%s_111" % str(yr.year)[-2:]
        self.project1 = ProjectFactory.create(
            prj_cd=prj_cd,
            owner=self.user,
            comment=self.commentStr,
            abstract=self.abstractStr,
            prj_nm=self.ProjectName,
        )

        prj_cd = "LHA_IA%s_222" % str(yr.year - 1)[-2:]
        self.project2 = ProjectFactory.create(prj_cd=prj_cd, owner=self.user)

        prj_cd = "LHA_IA%s_333" % str(yr.year - 2)[-2:]
        self.project3 = ProjectFactory.create(prj_cd=prj_cd, owner=self.user)

    def test_project_str(self):
        """make sure that the string representation of our project is
        what we expect (project name (project code))"""

        should_be = "%s (%s)" % (self.project1.prj_nm, self.project1.prj_cd)
        self.assertEqual(str(self.project1), should_be)

    def test_project_description(self):
        """verify that project description is return properly."""

        self.assertEqual(self.project1.description(), self.abstractStr)

    def test_project_name(self):
        """verify that project name is return properly."""

        self.assertEqual(self.project1.name(), self.ProjectName)

    def test_project_suffix(self):
        """verify that project suffix is the last three elements of
        the project code"""

        self.assertEqual(len(self.project1.project_suffix()), 3)
        should_be = self.project1.prj_cd[-3:]
        self.assertEqual(self.project1.project_suffix(), should_be)

    def test_project_save(self):
        """verify that the fields populated on save are what they
        should be"""
        prj_cd = "LHA_IA12_111"
        prj_nm = "Fake Project"
        project = ProjectFactory.create(prj_cd=prj_cd)

        project.save()
        should_be = prj_cd.lower()
        self.assertEqual(project.slug, should_be)
        should_be = "20" + prj_cd[6:8]
        self.assertEqual(str(project.year), should_be)

    def test_projects_this_year(self):
        """This one should return self.project1, but not project 2 or 3"""
        projects = Project.this_year.all()
        self.assertEqual(projects.count(), 1)
        self.assertEqual(projects[0].prj_cd, self.project1.prj_cd)

    def test_projects_last_year(self):
        """This one should return self.project2, but not project 1 or 3"""
        projects = Project.last_year.all()
        self.assertEqual(projects.count(), 1)
        self.assertEqual(projects[0].prj_cd, self.project2.prj_cd)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.user.delete()


@pytest.mark.django_db
def test_milestone_status_dict():
    """The milestone status dict method returns an ordered dictionary
    that contains each of the milestones assigned to a project and a
    status string that indicates if the milestone was associated with
    the project and if it has been complete.

    test for the presence and order of keys of the dictionary
    - test for the value of the entries.

    """

    # need four miles stones and a project.

    milestone1 = MilestoneFactory.create(
        label="Approved",
        label_abbrev="approved",
        category="Core",
        order=1,
        report=False,
    )

    milestone2 = MilestoneFactory.create(
        label="Proposal", label_abbrev="proposal", category="Core", order=2, report=True
    )

    milestone3 = MilestoneFactory.create(
        label="Draft Report",
        label_abbrev="draft-report",
        category="Core",
        order=3,
        report=True,
    )

    MilestoneFactory.create(
        label="Final Report",
        label_abbrev="final-report",
        category="Core",
        order=4,
        report=True,
    )

    project1 = ProjectFactory.create(prj_cd="LHA_IA12_111")

    # project1.initialize_milestones()

    # required and done
    pms = ProjectMilestones.objects.get(project=project1, milestone=milestone1)
    pms.completed = datetime.datetime.now(pytz.utc)
    pms.save()

    # not required but done anyway
    pms = ProjectMilestones.objects.get(project=project1, milestone=milestone2)
    pms.required = False
    pms.completed = datetime.datetime.now(pytz.utc)
    pms.save()

    # A report that is required and done
    pms = ProjectMilestones.objects.get(project=project1, milestone=milestone3)
    pms.completed = datetime.datetime.now(pytz.utc)
    pms.save()

    status_dict = project1.get_milestone_status_dict()

    milestones = ["approved", "proposal", "draft-report", "final-report", "custom"]

    types = ["milestone", "report", "report", "report", "report"]

    status = [
        "required-done",
        "notRequired-done",
        "required-done",
        "required-notDone",
        "notRequired-notDone",
    ]

    assert list(status_dict.keys()) == milestones

    # loop over our status dictionary and make sure that it contains
    # the elements we think it should:
    for i, ms in enumerate(milestones):
        tmp = status_dict.get(ms)
        assert tmp["type"] == types[i]
        assert tmp["status"] == status[i]


@pytest.mark.django_db
def test_milestone_status_dict_custom_report():
    """the ordered dictionary returned by the milestone_status_dict()
    method should include a key 'custom', the status of the
    milestone should be 'required-NotDone' and the type should be
    'report'
    """

    # need an additional custom milestone - one that is not core, but
    # specific to this project.

    milestone1 = MilestoneFactory.create(
        label="Custom Report",
        label_abbrev="my-custom-report",
        category="custom",
        order=1,
        report=True,
    )

    project1 = ProjectFactory.create(prj_cd="LHA_IA12_111")

    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone1, required=True, completed=None
    )

    status_dict = project1.get_milestone_status_dict()

    assert list(status_dict.keys()) == ["custom"]

    tmp = status_dict.get("custom")
    assert tmp["type"] == "report"
    assert tmp["status"] == "required-notDone"


@pytest.mark.django_db
def test_milestone_status_dict_custom_report_complete():
    """"""

    # we need custom report, and it should be completed.
    # the ordered dictionary returned by the milestone_status_dict()
    # method:
    # + should include a key 'custom',
    # + the status of the milestone should be 'required-Done'
    # + and the type should be 'report'

    milestone1 = MilestoneFactory.create(
        label="Custom Report",
        label_abbrev="my-custom-report",
        category="custom",
        order=1,
        report=True,
    )

    project1 = ProjectFactory.create(prj_cd="LHA_IA12_111")

    # this time, the project milestone is completed
    timestamp = datetime.datetime.now(pytz.utc)
    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone1, required=True, completed=timestamp
    )

    status_dict = project1.get_milestone_status_dict()

    assert list(status_dict.keys()) == ["custom"]

    tmp = status_dict.get("custom")
    assert tmp["type"] == "report"
    assert tmp["status"] == "required-done"


@pytest.mark.django_db
def test_milestone_status_dict_custom_reports():
    """The 'custom report' milestone is generic and applies to all custom
    reports for a project - multiple custom reports still result in
    only one 'custom' milestone in this dictionary.

    """

    # need an two additional custom milestones
    # the ordered dictionary returned by the milestone_status_dict()
    # method:
    # + should include a key 'custom',
    # + the status of the milestone should be 'required-Done'
    # + and the type should be 'report'

    milestone1 = MilestoneFactory.create(
        label="Custom Report",
        label_abbrev="my-custom-report",
        category="custom",
        order=1,
        report=True,
    )

    milestone2 = MilestoneFactory.create(
        label="Another Custom Report",
        label_abbrev="my-custom-report-2",
        category="custom",
        order=2,
        report=True,
    )

    project1 = ProjectFactory.create(prj_cd="LHA_IA12_111")

    # this time, the project milestone is Not completed
    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone1, required=True, completed=None
    )

    # this time, the project milestone is Not completed either
    pms2 = ProjectMilestonesFactory.create(
        project=project1, milestone=milestone2, required=True, completed=None
    )

    status_dict = project1.get_milestone_status_dict()

    assert list(status_dict.keys()) == ["custom"]

    tmp = status_dict.get("custom")
    assert tmp["type"] == "report"
    assert tmp["status"] == "required-notDone"


@pytest.mark.django_db
def test_milestone_status_dict_custom_reports_one_done():
    """The 'custom report' milestone is generic and applies to all custom
    reports for a project - multiple custom reports still result in
    only one 'custom' milestone in this dictionary.  If only one of
    the reports is complete, the status of the milestone should still
    be required-NotDone.

    """

    # need an two additional custom milestones - one will be complete,
    # one will not.
    # the ordered dictionary returned by the
    # milestone_status_dict() method: + should include a key 'custom',
    # + the status of the milestone should be 'required-NotDone' + and
    # the type should be 'report'

    milestone1 = MilestoneFactory.create(
        label="Custom Report",
        label_abbrev="my-custom-report",
        category="custom",
        order=1,
        report=True,
    )

    milestone2 = MilestoneFactory.create(
        label="Another Custom Report",
        label_abbrev="my-custom-report-2",
        category="custom",
        order=2,
        report=True,
    )

    project1 = ProjectFactory.create(prj_cd="LHA_IA12_111")

    # this time, the project milestone is Not completed
    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone1, required=True, completed=None
    )

    # this time, the project milestone is completed
    timestamp = datetime.datetime.now(pytz.utc)
    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone2, required=True, completed=timestamp
    )

    status_dict = project1.get_milestone_status_dict()

    assert list(status_dict.keys()) == ["custom"]

    tmp = status_dict.get("custom")
    assert tmp["type"] == "report"
    assert tmp["status"] == "required-notDone"


@pytest.mark.django_db
def test_milestone_status_dict_custom_reports_both_done():
    """The 'custom report' milestone is generic and applies to all custom
    reports for a project - multiple custom reports still result in
    only one 'custom' milestone in this dictionary.  The status of the
    milestone should be required-Done only if all of the custom
    requirements are complete.

    """

    # need an two additional custom milestones - one will be complete,
    # one will not to start.
    # the ordered dictionary returned by the
    # milestone_status_dict() method: + should include a key 'custom',
    # + the status of the milestone should be 'required-NotDone' + and
    # the type should be 'report'

    # when we complete the second custom milestone, and call our
    # milestone_status_dict() method again, the status will be changed
    # to 'required-Done'

    milestone1 = MilestoneFactory.create(
        label="Custom Report",
        label_abbrev="my-custom-report",
        category="custom",
        order=1,
        report=True,
    )

    milestone2 = MilestoneFactory.create(
        label="Another Custom Report",
        label_abbrev="my-custom-report-2",
        category="custom",
        order=2,
        report=True,
    )

    project1 = ProjectFactory.create(prj_cd="LHA_IA12_111")

    timestamp = datetime.datetime.now(pytz.utc)
    # this time, the project milestone is completed
    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone1, required=True, completed=timestamp
    )

    # this time, the project milestone is completed too
    ProjectMilestonesFactory.create(
        project=project1, milestone=milestone2, required=True, completed=timestamp
    )

    status_dict = project1.get_milestone_status_dict()

    assert list(status_dict.keys()) == ["custom"]

    tmp = status_dict.get("custom")
    assert tmp["type"] == "report"
    assert tmp["status"] == "required-done"


# @pytest.mark.django_db
# def test_project_total_cost():
#    """the total_cost() method should return the sum of salary and odoe
#    """
#
#    project = ProjectFactory.build(salary=1000)
#    assert project.odoe is None
#    assert project.salary == 1000
#    assert project.total_cost() == 1000
#
#    project = ProjectFactory.build(salary=1000, odoe=1000)
#    assert project.odoe == 1000
#    assert project.salary == 1000
#    assert project.total_cost() == 2000
#
#    project = ProjectFactory.build(odoe=1000)
#    assert project.odoe == 1000
#    assert project.salary is None
#    assert project.total_cost() == 1000
#
#    project = ProjectFactory.build()
#    assert project.odoe is None
#    assert project.salary is None
#    assert project.total_cost() == 0


@pytest.mark.django_db
def test_project_link_in_comments():
    """a simple little test to verify that the function replace_links is
    being called on project save and inserting the correct link into
    the projects html comment.

    """

    comment_text = """this is similar to project: LHA_IA11_123"""
    MilestoneFactory(label="Approved")
    project = ProjectFactory(comment=comment_text)
    project.save()

    link_string = '<a href="/projects/projectdetail/lha_ia11_123">' + "LHA_IA11_123</a>"
    assert link_string in project.comment_html


@pytest.mark.django_db
def test_multiple_project_links_in_comments():
    """If multiple project codes are passed in, they should all be
    replaced with hyperlinks.

    """
    MilestoneFactory(label="Approved")

    prj1 = "LHA_IA99_999"
    prj2 = "LHA_XX00_000"
    prj3 = "LHA_ZZ11_111"

    comment_text = (
        "this is similar to project: {0}, project: {1}, " + "and project: {2}"
    ).format(prj1, prj2, prj3)

    project = ProjectFactory(comment=comment_text)
    project.save()

    link_base = '<a href="/projects/projectdetail/{0}">{1}</a>'
    link_string = link_base.format(prj1.lower(), prj1.upper())
    assert link_string in project.comment_html

    link_string = link_base.format(prj2.lower(), prj2.upper())
    assert link_string in project.comment_html

    link_string = link_base.format(prj2.lower(), prj2.upper())
    assert link_string in project.comment_html


@pytest.mark.django_db
def test_project_links_case_insensitive():
    """Verify that project links should be replace regardless of the case
    of their letters.  Additionally they will be updated to have lower
    case url and uppercase project code.
    """

    MilestoneFactory(label="Approved")

    prj1 = "lha_ia99_999"  # all lower
    prj2 = "lha_XX00_000"  # mixed case
    prj3 = "LHA_ZZ11_111"  # all upper

    comment_text = (
        "this is similar to project: {0}, project: {1}, " + "and project: {2}"
    ).format(prj1, prj2, prj3)

    project = ProjectFactory(comment=comment_text)
    project.save()

    link_base = '<a href="/projects/projectdetail/{0}">{1}</a>'
    link_string = link_base.format(prj1.lower(), prj1.upper())
    assert link_string in project.comment_html

    link_string = link_base.format(prj2.lower(), prj2.upper())
    assert link_string in project.comment_html

    link_string = link_base.format(prj2.lower(), prj2.upper())
    assert link_string in project.comment_html


@pytest.mark.django_db
def test_project_link_in_risk():
    """a simple little test to verify that the function replace_links is
    being called on project save and inserting the correct link into
    the projects html comment.

    """

    risk_text = """this is similar to project: LHA_IA11_999"""
    MilestoneFactory(label="Approved")
    project = ProjectFactory(risk=risk_text)
    project.save()

    link_string = '<a href="/projects/projectdetail/lha_ia11_999">' + "LHA_IA11_999</a>"
    assert link_string in project.risk_html


class TestMilestoneModel(TestCase):
    def setUp(self):

        self.core1 = MilestoneFactory.create(
            label="core1", category="Core", order=1, report=True
        )
        self.core2 = MilestoneFactory.create(
            label="core2", category="Core", order=2, report=True
        )
        self.core3 = MilestoneFactory.create(
            label="core3", category="Core", order=3, report=True
        )
        self.custom = MilestoneFactory.create(
            label="custom", category="Custom", order=50, report=True
        )

        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Completed", category="Core", order=2, report=False
        )
        self.milestone3 = MilestoneFactory.create(
            label="Signoff", category="Core", order=999, report=False
        )
        self.customMS = MilestoneFactory.create(
            label="Aging", category="Custom", order=50, report=False
        )

        self.project = ProjectFactory.create()

    def test_initial_reports_on_save_method(self):
        """A record should be made automatically for each core report
        when a new project is created."""
        # make some fake reports, the three core reports should be
        # automatically associated with a new project, and verify that
        # the custom report is not when the project is created.

        myreports = ProjectMilestones.objects.filter(
            project=self.project, milestone__report=True
        )
        self.assertEqual(myreports.count(), 3)

        outstanding = self.project.get_outstanding()
        self.assertEqual(outstanding.count(), 3)

    def test_get_assigment_methods(self):

        assignments = self.project.get_reporting_requirements()
        cnt = assignments.count()
        self.assertEqual(cnt, 3)

        self.assertEqual(self.project.get_core_assignments().count(), 3)
        self.assertEqual(self.project.get_custom_assignments().count(), 0)

        # we haven't uploaded any reports, so this should be 0
        self.assertEqual(self.project.get_complete().count(), 0)

    def test_get_milestones(self):
        """by default, all core milestones are associated with project"""

        milestones = self.project.get_milestones()
        cnt = milestones.count()
        self.assertEqual(cnt, 3)
        self.assertNotEqual(cnt, 2)
        self.assertNotEqual(cnt, 4)

        # verify that the labels of my milestones appear in the correct order
        shouldbe = ["Approved", "Completed", "Signoff"]

        self.assertQuerysetEqual(
            milestones,
            ["Approved", "Completed", "Signoff"],
            lambda a: a.milestone.label,
        )

        # add the custom milestone to this project
        ProjectMilestones.objects.create(project=self.project, milestone=self.customMS)
        # verify that it appears in the milestone list for this project
        milestones = self.project.get_milestones()
        cnt = milestones.count()

        self.assertEqual(cnt, 4)
        self.assertQuerysetEqual(
            milestones,
            ["Approved", "Completed", "Aging", "Signoff"],
            lambda a: a.milestone.label,
        )

        # we changed our mind an aging is no longer required:
        ProjectMilestones.objects.filter(
            project=self.project, milestone=self.customMS
        ).update(required=False)

        milestones = self.project.get_milestones()
        cnt = milestones.count()

        self.assertEqual(cnt, 3)
        self.assertQuerysetEqual(
            milestones,
            ["Approved", "Completed", "Signoff"],
            lambda a: a.milestone.label,
        )

    def test_get_assigment_dicts(self):

        # dict = self.project.get_assignment_dicts()
        dict = self.project.get_milestone_dicts()
        print("dict.core = %s" % dict["Core"])
        print("dict.custom = %s" % dict["Custom"])

        core = dict["Core"]

        should_be = [self.core1.id, self.core2.id, self.core3.id]
        self.assertEqual(core["assigned"], should_be)

        reports = [str(x[1]) for x in core["milestones"]]
        self.assertEqual(
            reports, [self.core1.label, self.core2.label, self.core3.label]
        )

        custom = dict["Custom"]
        self.assertEqual(custom["assigned"], [])
        reports = [str(x[1]) for x in custom["milestones"]]
        self.assertEqual(reports, [self.custom.label])

    def test_get_assigment_methods_w_custom_report(self):

        """verify that custom reports are can be added and retrieved
        as expected."""

        custom1 = MilestoneFactory.create(
            label="custom1", report=True, category="Custom", order=99
        )

        projectreport = ProjectMilestonesFactory(
            project=self.project, milestone=custom1
        )

        self.assertEqual(self.project.get_reporting_requirements().count(), 4)
        self.assertNotEqual(self.project.get_reporting_requirements().count(), 3)
        self.assertNotEqual(self.project.get_reporting_requirements().count(), 5)

        self.assertEqual(self.project.get_core_assignments().count(), 3)
        self.assertEqual(self.project.get_custom_assignments().count(), 1)

        report = self.project.get_custom_assignments()[0]
        self.assertEqual(report.required, True)
        self.assertEqual(str(report.milestone), "custom1")

        # we haven't uploaded any reports, so this should be 0
        self.assertEqual(self.project.get_complete().count(), 0)

    def tearDown(self):

        self.core1.delete()
        self.core2.delete()
        self.core3.delete()
        self.custom.delete()

        self.milestone1.delete()
        self.milestone2.delete()
        self.milestone3.delete()
        self.customMS.delete()

        self.project.delete()


class TestModelReports(TestCase):
    """functions to test the models and methods assoicated with reports"""

    def setUp(self):

        # here are a couple of reports we will use, one will have a
        # report associated with it (complete), one will not (it will
        # be outstanding)
        self.core1 = MilestoneFactory.create(
            label="core1", report=True, category="Core", order=1
        )
        self.core2 = MilestoneFactory.create(
            label="core2", report=True, category="Core", order=2
        )
        MilestoneFactory(label="Approved")
        self.project = ProjectFactory.create()

        # retrieve the projectreport that would have been created for
        # the new project
        self.projectreport = ProjectMilestones.objects.get(
            project=self.project, milestone=self.core1
        )

        # create a fake report
        report = ReportFactory(report_path="path\to\fake\file.txt")
        # associate the report with the project reporting requirement
        report.projectreport.add(self.projectreport)

    def test_get_reporting_requirementss(self):
        rep = self.project.get_uploaded_reports()
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0].report_path, "path\to\fake\file.txt")
        # self.fail("Finish this test.")

    def test_get_completed(self):
        """a function to verify that the method to retrieve completed
        reporting requirements works."""
        comp = self.project.get_complete()
        self.assertEqual(len(comp), 1)

        # make sure that the project report objects match the attributes of core1 and self.project
        self.assertEqual(comp.values()[0]["required"], self.projectreport.required)
        self.assertEqual(
            comp.values()[0]["milestone_id"], self.projectreport.milestone_id
        )
        self.assertEqual(comp.values()[0]["project_id"], self.project.id)

        # verify that core2 isnt in the completed list - it isn't done yet:
        projids = [x["milestone_id"] for x in comp.values()]
        self.assertNotIn(self.core2.id, projids)

    def test_get_outstanding(self):
        """a test to verify that the method to retrieve unfinished
        reporting requirements works."""
        missing = self.project.get_outstanding()
        self.assertEqual(len(missing), 1)

        # make sure that the project report objects match the
        # attributes of core2 and self.project
        self.assertEqual(missing.values()[0]["required"], self.projectreport.required)
        self.assertEqual(missing.values()[0]["milestone_id"], self.core2.id)
        self.assertEqual(missing.values()[0]["project_id"], self.project.id)

        # verify that core1 isnt in the missing list - it was completed
        # during setup
        projids = [x["milestone_id"] for x in missing.values()]
        self.assertNotIn(self.core1.id, projids)

    def tearDown(self):
        self.project.delete()
        self.projectreport.delete()


class TestModelSisters(TestCase):
    """make sure we can add and delete sisters to projects and that
    families are created and cleaned when not needed."""

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.lake0 = LakeFactory(abbrev="HU", lake_name="Lake Huron")
        self.lake1 = LakeFactory(abbrev="ON", lake_name="Lake Ontario")

        self.ProjType = ProjTypeFactory()
        self.ProjType2 = ProjTypeFactory(project_type="Nearshore Index")

        self.protocol0 = ProjProtocolFactory(
            protocol="Fall Walleye Index Netting", abbrev="FWIN"
        )
        self.protocol1 = ProjProtocolFactory(
            protocol="Broad Scale Monitoring", abbrev="BSM"
        )

        # add in protocols here - differnt protocols cannot be sisters

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        # projects this project is a differnt protocol and should not
        # be a canditate sister
        self.project0 = ProjectFactory.create(
            prj_cd="LHA_IA12_000",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol0,
        )

        self.project1 = ProjectFactory.create(
            prj_cd="LHA_IA12_111",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        self.project2 = ProjectFactory.create(
            prj_cd="LHA_IA12_222",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        self.project3 = ProjectFactory.create(
            prj_cd="LHA_IA12_333",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        self.project4 = ProjectFactory.create(
            prj_cd="LHA_IA12_444",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        self.project5 = ProjectFactory.create(
            prj_cd="LHA_IA12_555",
            owner=self.user,
            project_type=self.ProjType2,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        self.project6 = ProjectFactory.create(
            prj_cd="LHA_IA11_666",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake1,
            protocol=self.protocol1,
        )

        self.project7 = ProjectFactory.create(
            prj_cd="LOA_IA11_999",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake1,
            protocol=self.protocol1,
        )

        self.project0.approve()
        self.project1.approve()
        self.project2.approve()
        self.project3.approve()
        # self.project4.approve()  - #4 Not Approved
        self.project5.approve()
        self.project6.approve()
        self.project7.approve()  # different Lake

    def test_sisters(self):

        # make sure that the family table is empty
        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt, 0)

        self.assertEqual(self.project1.get_sisters(), [])
        self.assertEqual(self.project1.get_family(), None)

        candidates = self.project1.get_sister_candidates()
        self.assertEqual(candidates.count(), 2)

        # make project 1 and 2 sisters:
        self.project1.add_sister(self.project2.slug)

        # verify that they are sisters and have the same family
        sisters1 = self.project1.get_sisters()
        sisters2 = self.project2.get_sisters()
        # and there they each only have one candidate:
        candidates = self.project1.get_sister_candidates()
        self.assertEqual(candidates.count(), 1)
        candidates = self.project2.get_sister_candidates()
        self.assertEqual(candidates.count(), 1)

        # each sister should return the other:
        self.assertEqual(sisters1[0].prj_cd, "LHA_IA12_222")
        self.assertEqual(sisters2[0].prj_cd, "LHA_IA12_111")

        # and they should all be in the same family
        self.assertEqual(self.project1.get_family(), self.project2.get_family())
        # project3 should not have a family
        self.assertEqual(self.project3.get_family(), None)

        # make project3 a sistser of project2
        self.project2.add_sister(self.project3.slug)
        # automatically it should be a sister of project1
        sisters1 = self.project1.get_sisters()
        sisters2 = self.project2.get_sisters()
        sisters3 = self.project3.get_sisters()

        # order changes sometimes and doesn't matter, as long as the
        # project codes are in the returned values:
        prj_cds = [x.prj_cd for x in sisters1]
        self.assertIn("LHA_IA12_222", prj_cds)
        self.assertIn("LHA_IA12_333", prj_cds)

        # self.assertEqual(sisters1[2].prj_cd,"LHA_IA12_333")

        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt, 1)

        # there shouldn't be any candidates - there all sisters now
        candidates = self.project1.get_sister_candidates()
        self.assertEqual(list(candidates), [])
        self.assertEqual(candidates.count(), 0)

        # remove project2 from the family
        self.project1.delete_sister(self.project2.slug)
        self.assertEqual(self.project2.get_sisters(), [])
        self.assertEqual(self.project2.get_family(), None)
        # self.assertEqual(self.project1.get_sisters(), self.project3.get_sisters())
        self.assertEqual(self.project1.get_family(), self.project3.get_family())

        # delete the last sister and verify that everything is empty
        self.project1.delete_sister(self.project3.slug)
        self.assertEqual(self.project1.get_sisters(), [])
        self.assertEqual(self.project1.get_family(), None)
        self.assertEqual(self.project2.get_sisters(), [])
        self.assertEqual(self.project2.get_family(), None)
        self.assertEqual(self.project3.get_sisters(), [])
        self.assertEqual(self.project3.get_family(), None)

        # make sure that the family table is empty again
        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt, 0)

    def test_sisters_include_self(self):

        # make sure that the family table is empty
        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt, 0)

        # make project 1 and 2 sisters:
        self.project1.add_sister(self.project2.slug)

        # verify that they are sisters and have the same family
        sisters1 = self.project1.get_sisters(False)
        sisters2 = self.project2.get_sisters(False)

        self.assertQuerysetEqual(
            sisters1,
            [self.project1.prj_cd, self.project2.prj_cd],
            lambda a: a.prj_cd,
            ordered=False,
        )

        self.assertQuerysetEqual(
            sisters2, [self.project1.prj_cd, self.project2.prj_cd], lambda a: a.prj_cd
        )

    def test_has_sisters(self):
        """has_sisters() is a simple method of project objects.  Returns True
        if the object has one or more sisters, false otherwise.

        """
        # make project 1 and 2 sisters:
        self.project1.add_sister(self.project2.slug)

        self.assertTrue(self.project1.has_sister())
        self.assertTrue(self.project2.has_sister())
        # number three should not have any sisters
        self.assertFalse(self.project3.has_sister())

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.project4.delete()
        self.project5.delete()
        self.project6.delete()
        self.project7.delete()
        self.ProjType.delete()
        self.ProjType2.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.lake0.delete()
        self.lake1.delete()
        self.user.delete()


class TestModelBookmarks(TestCase):
    """Verify that the bookmark objects return the data in the
    expected format."""

    def setUp(self):
        """we will need three projects with easy to rember project
        codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.user2 = UserFactory(
            username="mburns", first_name="Monty", last_name="Burns"
        )

        MilestoneFactory(label="Approved")

        self.ProjType = ProjTypeFactory(project_type="Nearshore Index")

        self.project = ProjectFactory.create(
            prj_cd="LHA_IA12_111", project_type=self.ProjType
        )

    def test_BookmarkAttributes(self):
        """Verify that bookmark methods retrun expected values"""
        bookmark = Bookmark.objects.create(user=self.user, project=self.project)

        self.assertEqual(bookmark.get_project_code(), self.project.prj_cd)
        self.assertEqual(bookmark.get_project_url(), self.project.get_absolute_url())
        self.assertEqual(bookmark.year(), self.project.year)
        self.assertEqual(str(bookmark), str(self.project))
        self.assertEqual(bookmark.name(), self.project.prj_nm)
        self.assertEqual(bookmark.project_type(), self.project.project_type)

    def test_bookmark_get_watchers_method(self):
        """This function should return a list of users who are watching this
        project.  This function is need to help build the message
        distribution list
        """

        # homer bookmarks this project
        bookmark = Bookmark.objects.create(user=self.user, project=self.project)
        watchers = bookmark.get_watchers()
        self.assertEqual(watchers[0], self.user)

        # Mr Burns bookmarks this project too
        bookmark = Bookmark.objects.create(user=self.user2, project=self.project)
        watchers = bookmark.get_watchers()

        shouldbe = [self.user, self.user2]
        self.assertCountEqual(watchers, shouldbe)

    def tearDown(self):
        self.project.delete()
        self.ProjType.delete()
        self.user.delete()
        self.user2.delete()


class TestProjectTagging(TestCase):
    """make sure we can add and delete tags, and retrieve all projects
    associated with a given tag."""

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )
        MilestoneFactory(label="Approved")
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222", owner=self.user)
        self.project3 = ProjectFactory.create(prj_cd="LHA_IA12_333", owner=self.user)

    def test_add_remove_tags(self):
        """verify that we can add and remove tags to a project"""
        self.assertEqual(len(self.project1.tags.all()), 0)
        self.project1.tags.add("perch", "walleye", "whitefish")
        self.assertEqual(len(self.project1.tags.all()), 3)

        tags = self.project1.tags.all()
        for tag in tags:
            self.assertTrue(str(tag) in ["perch", "walleye", "whitefish"])
        # assert 3==0

        self.project1.tags.remove("perch")
        tags = self.project1.tags.all()
        self.assertEqual(tags.count(), 2)
        for tag in tags:
            self.assertTrue(str(tag) in ["walleye", "whitefish"])
        self.assertFalse("perch" in tags)

        self.project1.tags.clear()
        self.assertEqual(len(self.project1.tags.all()), 0)

    def test_filter_projects_by_tags(self):
        """verify that we can get projects with the same tag"""

        self.assertEqual(len(self.project1.tags.all()), 0)
        self.project1.tags.add("project1", "project12", "allprojects")
        self.project2.tags.add("project2", "project12", "allprojects")
        self.project3.tags.add("project3", "allprojects")

        observed = [
            x[0]
            for x in Project.objects.filter(tags__name__in=["allprojects"]).values_list(
                "prj_cd"
            )
        ]
        self.assertEqual(len(observed), 3)
        expected = [x.prj_cd for x in [self.project1, self.project2, self.project3]]
        self.assertEqual(set(expected), set(observed))

        projects = Project.objects.filter(tags__name__in=["project12"])
        self.assertEqual(projects.count(), 2)
        self.assertQuerysetEqual(
            projects,
            [self.project1.prj_cd, self.project2.prj_cd],
            lambda a: a.prj_cd,
            ordered=False,
        )

        projects = Project.objects.filter(tags__name__in=["project1"])
        self.assertEqual(projects.count(), 1)
        self.assertEqual(projects[0].prj_cd, self.project1.prj_cd)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()


class TestEmployeeFunctions(TestCase):
    def setUp(self):

        self.user1 = UserFactory(
            first_name="Jerry", last_name="Seinfield", username="jseinfield"
        )

        self.user2 = UserFactory(
            first_name="George", last_name="Costanza", username="gcostanza"
        )

        self.user3 = UserFactory(
            first_name="Cosmo", last_name="Kramer", username="ckramer"
        )
        self.user4 = UserFactory(
            first_name="Elaine", last_name="Benis", username="ebenis"
        )
        self.user5 = UserFactory(
            first_name="Kenny", last_name="Banya", username="kbanya"
        )

        self.user6 = UserFactory(
            first_name="Ruteger", last_name="Newm", username="rnewman"
        )

        # now setup employee relationships

        self.employee1 = EmployeeFactory(user=self.user1)
        self.employee2 = EmployeeFactory(user=self.user2, supervisor=self.employee1)
        self.employee3 = EmployeeFactory(user=self.user3, supervisor=self.employee1)
        self.employee4 = EmployeeFactory(user=self.user4, supervisor=self.employee3)
        self.employee5 = EmployeeFactory(user=self.user5, supervisor=self.employee3)
        self.employee6 = EmployeeFactory(user=self.user6, supervisor=self.employee5)

        # Jerry is everyone's boss
        # Jerry's direct reports are George and Kramer
        # Elaine reports to Kramer
        # Banya reports to Kramer
        # Newman reports to Banya

    def test_get_supervisors(self):

        # for Jerry, get supervisors will return just him
        bosses = get_supervisors(self.employee1)
        shouldbe = [self.employee1]
        bosses = [str(x) for x in bosses]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        # for George get_supervisor will return he and Jerry
        bosses = get_supervisors(self.employee2)
        shouldbe = [self.employee2, self.employee1]
        bosses = [str(x) for x in bosses]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        # for Kramer get_supervisor will return he and Jerry
        bosses = get_supervisors(self.employee3)
        shouldbe = [self.employee3, self.employee1]
        bosses = [str(x) for x in bosses]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        # for Elaine get_supervisor will return her, Kramer and Jerry
        bosses = get_supervisors(self.employee4)
        shouldbe = [self.employee4, self.employee3, self.employee1]
        bosses = [str(x) for x in bosses]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        # for Banya get_supervisor will return he, Kramer and Jerry
        bosses = get_supervisors(self.employee5)
        shouldbe = [self.employee5, self.employee3, self.employee1]
        bosses = [str(x) for x in bosses]
        shouldbe = [str(x) for x in shouldbe]
        self.assertEqual(bosses, shouldbe)

        # for Newman get_supervisor will return he, Banya, Kramer and Jerry
        bosses = get_supervisors(self.employee6)
        shouldbe = [self.employee6, self.employee5, self.employee3, self.employee1]
        bosses = [str(x) for x in bosses]
        shouldbe = [str(x) for x in shouldbe]
        self.assertEqual(bosses, shouldbe)

    def test_get_minions(self):

        # George, Elaine and Newman don't have anyone working for
        # them, so get_minions shouldn't return anyone but them for
        # George, get_minions will return just him
        minions = get_minions(self.employee2)
        shouldbe = [self.employee2]
        minions = [str(x) for x in minions]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(minions, shouldbe)

        # Banya is Newman's boss.  get_minions for Banya should return
        # both Banya and Newman
        minions = get_minions(self.employee5)
        shouldbe = [self.employee5, self.employee6]
        minions = [str(x) for x in minions]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(minions, shouldbe)

        # Kramer supervises Elaine and Banya directly, Banya
        # supervises Newman get_minions(Kramer) should return all four
        # employees.
        minions = get_minions(self.employee3)
        shouldbe = [self.employee3, self.employee4, self.employee5, self.employee6]
        minions = [str(x) for x in minions]
        shouldbe = [str(x) for x in shouldbe]
        self.assertListEqual(minions, shouldbe)

        # Jerry supervises everyone either directly or indirectly
        # get_minions(Jerry) should return all employees.
        minions = get_minions(self.employee1)
        shouldbe = [
            self.employee1,
            self.employee2,
            self.employee3,
            self.employee4,
            self.employee5,
            self.employee6,
        ]
        minions = [str(x) for x in minions]
        shouldbe = [str(x) for x in shouldbe]

        minions.sort()
        shouldbe.sort()

        self.assertListEqual(minions, shouldbe)

    def tearDown(self):

        self.employee1.delete()
        self.employee2.delete()
        self.employee3.delete()
        self.employee4.delete()
        self.employee5.delete()
        self.employee6.delete()

        self.user1.delete()
        self.user2.delete()
        self.user3.delete()
        self.user4.delete()
        self.user5.delete()
        self.user6.delete()


class TestMilestoneStatus(TestCase):
    """This suite of tests are to verify that the project method
    'milestone_complete' works as expected.  If a milestone has not
    been assigned to a project it should return None, if a milestone
    has been assigned but is still incomplete it should return False,
    and finally if it has been assigned and is complete, it should return true.

    There is also a test that verifies that milestones that have been
    revoked are returned as incomplete (False).

    """

    def setUp(self):
        """we will need one project with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )

        self.milestone2 = MilestoneFactory.create(
            label="Completed", category="Core", order=2, report=False
        )

        self.milestone2 = MilestoneFactory.create(
            label="Sign Off", category="Core", order=3, report=False
        )

        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)

    def test_somthing_other_than_milestones(self):
        """if we try to pass in something other than a milestone, we should
        handle it gracefully - return None"""

        # we pass in a non-sensical value, return None
        self.assertEqual(self.project1.milestone_complete("foobar"), None)

    def test_incomplete_milestones(self):
        """If the milestone has been applied to the project but is still
        incomplete, return False.  This test takes advantage of the
        fact that all core requirements are automatically added when
        project is created.

        """
        # this milestone hasn't been completed, our function should return false
        self.assertFalse(self.project1.milestone_complete(self.milestone2))

    def test_complete_milestones(self):
        """If the milestone has been applied to the project and has been
        completed, return True"""

        # verify that our function returns False before we start
        self.assertFalse(self.project1.milestone_complete(self.milestone1))
        # use the project approve method to satisfy that milestone
        self.project1.approve()
        # verify that our function returns True now
        self.assertTrue(self.project1.milestone_complete(self.milestone1))

    def test_unassigned_milestones(self):
        """an assigned milestone should return None"""

        # this is a new milestone, it won't be associated with this
        # project.  If we pass it into our method, we should get back
        # None.
        new_milestone = MilestoneFactory.create(
            label="UnAssigned Milestone", category="Core", order=999, report=False
        )

        self.assertEqual(self.project1.milestone_complete(new_milestone), None)

    def test_revoked_milestones(self):
        """a milestone that was satisfied, but then revoked by manager should
        be incomplete again"""

        # verify that it's not complete first
        self.assertFalse(self.project1.milestone_complete(self.milestone1))
        self.project1.approve()
        # now it is
        self.assertTrue(self.project1.milestone_complete(self.milestone1))
        # oh-oh it's been revoked!
        self.project1.unapprove()
        # our function should now return false
        self.assertFalse(self.project1.milestone_complete(self.milestone1))

    def tearDown(self):

        self.project1.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.user.delete()


class TestProjdectFundingProperties(TestCase):
    """test the methods/model properies used to summarize the costs by
    source for Project objects.
    """

    def setUp(self):
        """To test the methods we will need a project and at least two funding
        sources."""

        MilestoneFactory(label="Approved")
        self.project = ProjectFactory.create(prj_cd="LHA_IA99_123")
        self.source1 = FundingSourceFactory.create(abbrev="spa")
        self.source2 = FundingSourceFactory.create(name="COA", abbrev="coa")
        self.projectfunding1 = ProjectFundingFactory.create(
            project=self.project, source=self.source1, odoe=1000, salary=5000
        )

        self.projectfunding2 = ProjectFundingFactory.create(
            project=self.project, source=self.source2, odoe=2000, salary=8000
        )

    def test_project_total_odoe(self):
        """the total odoe should be sum of the odoe of the funding sources
        assocaited with our project."""

        self.assertEqual(self.project.total_odoe, 3000)

    def test_project_total_salary(self):
        """the total salary should be sum of the salary of the funding sources
        assocaited with our project."""

        self.assertEqual(self.project.total_salary, 13000)

    def test_project_total_cost(self):
        """the total cost of should be sum of the salary and odoe of the
        funding sources assocaited with our project.

        """

        self.assertEqual(self.project.total_cost, 16000)

    def tearDown(self):

        self.projectfunding2.delete()
        self.projectfunding1.delete()

        self.source1.delete()
        self.source2.delete()
        self.project.delete()


class TestProjectFunding(TestCase):
    """test the methods associated with our funding source model."""

    def setUp(self):
        """"""

        MilestoneFactory(label="Approved")
        self.project = ProjectFactory.create(prj_cd="LHA_IA99_123")
        self.fundingsource = FundingSourceFactory.create(abbrev="spa")

        self.projectfunding = ProjectFundingFactory.create(
            project=self.project, source=self.fundingsource, odoe=1000, salary=5000
        )

    def test_funding_source_repr(self):
        """the string representation of our model should include the project
        code and the funding source.  <LHA_IA99_123 - spa>"""

        should_be = "<LHA_IA99_123 - spa>"
        self.assertEqual(str(self.projectfunding), should_be)

    def test_funding_source_total(self):
        """The total method of the funding source model is the sum of the odoe
        and salary elements."""

        self.assertEqual(self.projectfunding.total, 6000)

    def test_funding_source_total_null_salary(self):
        """If the salary is null, the total should return just the odeo (treat
        salary as 0)"""
        self.projectfunding.salary = None
        self.assertEqual(self.projectfunding.total, 1000)

    def test_funding_source_total_null_odoe(self):
        """If the odoe is null, the total should return just the odeo (treat
        odoe as 0)"""
        self.projectfunding.odoe = None
        self.assertEqual(self.projectfunding.total, 5000)

    def test_funding_source_total_null_odoe_null_salary(self):
        """If both odoe and salary are null, the total should be 0 (treat both
        null values as 0)"""
        self.projectfunding.odoe = None
        self.projectfunding.salary = None
        self.assertEqual(self.projectfunding.total, 0)

    def tearDown(self):

        self.projectfunding.delete()
        self.fundingsource.delete()
        self.project.delete()


class TestFundingSource(TestCase):
    """test the methods associated with our funding source model."""

    def setUp(self):
        """"""

        source = "Special Purpose Account"
        self.fundingsource = FundingSourceFactory(name=source, abbrev="spa")

    def test_funding_source_repr(self):
        """the string representation of our model should include the project
        code and the funding source.  'Special Purpose Account (spa)'"""

        should_be = "Special Purpose Account (spa)"
        self.assertEqual(str(self.fundingsource), should_be)

    def tearDown(self):

        self.fundingsource.delete()


class TestProjectStatus(TestCase):
    """The status of a project must be one of: 'Submitted', 'Ongoing',
        'Cancelled' or 'Complete'
        Submitted - not approved
        Ongoing - approved, but not cancelled or signed off
        Cancelled - cancelled==True
        Complete - signoff==True

    We need to verify that project.status returns the correct values.

    """

    def setUp(self):
        """we will need three projects with easy to rember project codes"""

        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # Add milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=2, report=False
        )

        self.milestone3 = MilestoneFactory.create(
            label="Cancelled", category="Core", order=3, report=False
        )
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)

    def test_status_submitted(self):
        """if a project has been submitted, but has not been approved,
        cancelled or signed off, it should be submitted.
        """
        self.assertEqual(self.project1._get_status(), "Submitted")
        self.assertEqual(self.project1.status, "submitted")

    def test_status_ongoing(self):
        """if a project has been submitted, but has not been approved,
        cancelled or signed off, it should be submitted.
        """
        self.project1.approve()
        self.assertEqual(self.project1._get_status(), "Ongoing")
        self.assertEqual(self.project1.status, "ongoing")

    def test_status_cancelled(self):
        """if a project has been submitted, but has not been approved,
        cancelled or signed off, it should be submitted.
        """
        self.project1.cancel(self.user)

        self.assertTrue(self.project1.cancelled)
        self.assertEqual(self.project1._get_status(), "Cancelled")
        self.assertEqual(self.project1.status, "cancelled")

    def test_status_complete(self):
        """if a project has been submitted, but has not been approved,
        cancelled or signed off, it should be submitted.
        """
        self.project1.approve()
        self.project1.signoff(self.user)
        self.assertEqual(self.project1._get_status(), "Complete")
        self.assertEqual(self.project1.status, "complete")
