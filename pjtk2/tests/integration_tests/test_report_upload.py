"""Tests in this file use both web test and the django test client to
verify that the report upload formset is rendered properly and uploads
files as expected."""


import os
import re
from io import StringIO

import pytest
from django.conf import settings
from django.db.models.signals import pre_save
from django.test import TestCase
from django.urls import reverse
from django_webtest import WebTest
from pjtk2.models import ProjectMilestones
from pjtk2.tests.factories import *

UPLOAD_TO = "milestone_reports"


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


class BasicReportUploadTestCase(WebTest):
    """
    NOTE - actual file upload tests moved to the bottom of the is
    file couldn't get webtest to include uploaded files in
    request.FILEs.  These webtest tests verify that the report upload
    form is rendered correctly."""

    def setUp(self):
        # USER
        self.user = UserFactory.create(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # required reports
        self.rep1 = MilestoneFactory.create(
            label="Proposal Presentation", category="Core", order=1, report=True
        )
        self.rep2 = MilestoneFactory.create(
            label="Completion Report", category="Core", order=2, report=True
        )
        self.rep3 = MilestoneFactory.create(
            label="Summary Report", shared=True, category="Core", order=3, report=True
        )
        self.rep4 = MilestoneFactory.create(
            label="Budget Report", category="Custom", order=99, report=True
        )

        # PROJECTS
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222", owner=self.user)
        self.project3 = ProjectFactory.create(prj_cd="LHA_IA12_333", owner=self.user)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project1, milestone=signoff)
        ProjectMilestonesFactory(project=self.project2, milestone=signoff)
        ProjectMilestonesFactory(project=self.project3, milestone=signoff)

        # here is fake file that we will upload
        self.mock_file = StringIO(
            "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00"
            "\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )

        self.mock_file.name = "path/to/some/fake/fake_test_file.txt"

        self.mock_file2 = StringIO(
            "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00"
            "\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        self.mock_file2.name = "path/to/some/fake/fake_test_file-2.txt"

        self.mock_file3 = StringIO(
            "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00"
            "\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        self.mock_file3.name = "path/to/some/fake/fake_test_file-3.txt"

    def test_render_report_upload_form(self):

        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        # verify the basic elements of the page
        self.assertIn("Upload Reports", response)
        self.assertIn(self.project1.prj_cd, response)
        self.assertIn(self.project1.prj_nm, response)

        # each of the core reports should be the response by default:
        self.assertIn(self.rep1.label, response)
        self.assertIn(self.rep2.label, response)
        self.assertIn(self.rep3.label, response)

        # the fourth report is not core, and has not been assigned to
        # this project.  It should not be in the response:
        self.assertNotIn(self.rep4.label, response)

        form = response.forms["uploadreports"]
        # there should be four forms in the formset
        formcnt = len([x for x in form.fields.keys() if x.endswith("-report_path")])
        self.assertEqual(formcnt, 3)

    def test_render_report_upload_form_custom(self):
        """exactly the same as previous test but with a requirement
        for a custom report"""
        requirement_count = self.project1.get_reporting_requirements().count()
        self.assertEqual(requirement_count, 3)

        ProjectMilestones.objects.create(project=self.project1, milestone=self.rep4)
        # verify that this project now has 4 reporting requirements

        requirement_count = self.project1.get_reporting_requirements().count()
        self.assertEqual(requirement_count, 4)

        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        # verify the basic elements of the page
        self.assertIn("Upload Reports", response)
        self.assertIn(self.project1.prj_cd, response)
        self.assertIn(self.project1.prj_nm, response)

        # each of the core reports should be the response by default:
        self.assertIn(self.rep1.label, response)
        self.assertIn(self.rep2.label, response)
        self.assertIn(self.rep3.label, response)

        # the fourth should now be included in the response
        self.assertIn(self.rep4.label, response)

        form = response.forms["uploadreports"]
        # there should be four forms in the formset
        formcnt = len([x for x in form.fields.keys() if x.endswith("-report_path")])
        self.assertEqual(formcnt, 4)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.user.delete()
        self.rep1.delete()
        self.rep2.delete()

        # finally get rid of the temporary file if it was created in
        # this test
        # mock_file1
        filepath = os.path.join(
            settings.MEDIA_ROOT, UPLOAD_TO, os.path.split(self.mock_file.name)[1]
        )
        try:
            os.remove(filepath)
        except:
            pass

        # mock_file2
        filepath = os.path.join(
            settings.MEDIA_ROOT, UPLOAD_TO, os.path.split(self.mock_file2.name)[1]
        )
        try:
            os.remove(filepath)
        except:
            pass

        # mock_file3
        filepath = os.path.join(
            settings.MEDIA_ROOT, UPLOAD_TO, os.path.split(self.mock_file3.name)[1]
        )
        try:
            os.remove(filepath)
        except:
            pass

        # finally, clean out any test files that may have been
        # duplicates and named slightly differently than the others.
        media_dir = os.path.join(settings.MEDIA_ROOT, UPLOAD_TO)
        pattern = r"fake_test_file.*\.txt"
        files = [f for f in os.listdir(media_dir) if re.match(pattern, f)]

        for fname in files:
            filepath = os.path.join(settings.MEDIA_ROOT, fname)
            try:
                print("deleting={}".format(fname))
                os.remove(filepath)
            except:
                pass


class TestActualFileUpload(TestCase):
    """These tests use the django test client to upload reports
    associated with different reporting requirements."""

    def setUp(self):
        # USER
        self.user = UserFactory.create(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # required reports (rep0 and rep2 are shared)
        self.rep0 = MilestoneFactory.create(
            label="Proposal Presentation",
            shared=True,
            category="Core",
            order=1,
            report=True,
        )
        self.rep1 = MilestoneFactory.create(
            label="Completion Report", category="Core", order=2, report=True
        )
        self.rep2 = MilestoneFactory.create(
            label="Summary Report", shared=True, category="Core", order=3, report=True
        )
        self.rep3 = MilestoneFactory.create(
            label="Budget Report", category="Custom", order=99, report=True
        )

        # PROJECTS
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", owner=self.user)
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222", owner=self.user)
        self.project3 = ProjectFactory.create(prj_cd="LHA_IA12_333", owner=self.user)

        signoff = MilestoneFactory(label="Sign Off")
        ProjectMilestonesFactory(project=self.project1, milestone=signoff)
        ProjectMilestonesFactory(project=self.project2, milestone=signoff)
        ProjectMilestonesFactory(project=self.project3, milestone=signoff)

        # here is fake file that we will upload
        self.mock_file0 = StringIO(
            "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00"
            "\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        self.mock_file0.name = "path/to/some/fake/fake_test_file.txt"

        self.mock_file1 = StringIO(
            "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00"
            "\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        self.mock_file1.name = "path/to/some/fake/fake_test_file-1.txt"

        self.mock_file2 = StringIO(
            "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00"
            "\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        self.mock_file2.name = "path/to/some/fake/fake_test_file-2.txt"

    def test_upload_single_report(self):
        """verify that a user can upload a simple file, that the file
        is associated with the correct project and has the correct
        report-type."""

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        form_data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-0-report_path": self.mock_file0,
        }

        self.client.post(url, form_data)

        # verify that the report was added to the Report table:
        report_count = Report.objects.all().count()
        self.assertEqual(report_count, 1)

        filepath = os.path.join(
            "milestone_reports", os.path.split(self.mock_file0.name)[1]
        ).replace("\\", "/")

        reports = self.project1.get_uploaded_reports()
        self.assertEqual(reports.values()[0]["report_path"], filepath)

        # make sure that the milestone is what we think it is:
        pr = ProjectMilestones.objects.get(report=reports.select_related()[0])
        self.assertEqual(pr.milestone, self.rep0)

        # verify that a link to the file is on the project details page
        url = reverse("project_detail", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath,)),
            filepath,
        )

        self.assertContains(response, linkstring)

    def test_can_download_a_single_report(self):
        """verify that a user can actually download."""

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        form_data = {
            "form-TOTAL_FORMS": 1,
            "form-INITIAL_FORMS": 0,
            "form-0-report_path": self.mock_file0,
        }

        self.client.post(url, form_data)

        # verify that the report was added to the Report table:
        report_count = Report.objects.all().count()
        self.assertEqual(report_count, 1)

        # verify that we can download the file we just uploaded:

        filepath = os.path.join(UPLOAD_TO, os.path.split(self.mock_file0.name)[1])

        url = reverse("serve_file", args=(filepath,))
        response = self.client.get(url)

        filepath = os.path.split(filepath)[1]
        self.assertEqual(
            response.get("Content-Disposition"), "attachment; filename=%s" % filepath
        )

    def test_upload_multiple_reports(self):
        """verify that we can upload more than 1 file"""

        # create a requirement for a budget report for this poject
        ProjectMilestones.objects.create(project=self.project1, milestone=self.rep3)

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        # upload mock_file1 to "Project Proposal" file field
        # upload mock_file2 to "Summary" file field
        # upload mock_file3 to "Budget Report" file field

        form_data = {
            "form-TOTAL_FORMS": 4,
            "form-INITIAL_FORMS": 4,
            "form-0-report_path": self.mock_file0,
            # form-1-report_path - leave empty should be Proj. Completion
            "form-2-report_path": self.mock_file1,
            "form-3-report_path": self.mock_file2,
        }

        # submit the report
        self.client.post(url, form_data)

        # get the all of the reports and the proejct-reports assocaited
        # with this project
        reports = Report.objects.all()

        # verify that three reports have been added to the Report table:
        self.assertEqual(reports.count(), 3)

        # first file:
        filepath1 = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file0.name)[1]
        ).replace("\\", "/")
        self.assertEqual(reports.values()[0]["report_path"], filepath1)

        # make sure that the milestone is what we think it is:
        # there should only be one projectreport record associate with
        # this report, and its report type should match that of rep1
        pr = reports[0].projectreport.all()
        self.assertEqual(pr.count(), 1)
        self.assertEqual(pr[0].milestone, self.rep0)

        # =============
        # second file:
        filepath2 = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file1.name)[1]
        ).replace("\\", "/")

        self.assertEqual(reports.values()[1]["report_path"], filepath2)
        report_id = reports.values_list()[1][0]

        # make sure that the milestone is what we think it is:
        # there should only be one projectreport record associate with
        # this report, and its report type should match that of rep1
        pr = ProjectMilestones.objects.filter(report__id=report_id)
        self.assertEqual(pr.count(), 1)
        # we skipped a file on the form - this should be associated
        # with the 3rd milestone
        self.assertEqual(pr[0].milestone, self.rep2)

        # =============
        # third file:
        filepath3 = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file2.name)[1]
        ).replace("\\", "/")
        self.assertEqual(reports.values()[2]["report_path"], filepath3)
        report_id = reports.values_list()[2][0]
        # make sure that the milestone is what we think it is:
        # there should only be one projectreport record associate with
        # this report, and its report type should match that of rep1
        pr = ProjectMilestones.objects.filter(report__id=report_id)
        self.assertEqual(pr.count(), 1)
        self.assertEqual(pr[0].milestone, self.rep3)

        # =============
        # verify that a link to the file is on the project details page
        url = reverse("project_detail", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath1,)),
            filepath1,
        )
        self.assertContains(response, linkstring)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath2,)),
            filepath2,
        )
        self.assertContains(response, linkstring)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath3,)),
            filepath3,
        )
        self.assertContains(response, linkstring)

        # verify that the file names are on the project details page
        # verify that the file names are associated with the
        # appropriate report type

        # verify that the file names are in queryset returned by  get_uploaded_reports()

    def test_upload_report_sister_report_message(self):
        """verify that the fields are hightlighted and the message about
        shared reports is included in the response."""

        # set up the sister relationship:
        self.project1.add_sister(self.project2.slug)

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        self.assertContains(response, 'id="shared-milestone-message"')
        self.assertContains(response, 'class="fileinput shared"')

    def test_upload_report_sister_report_message_not_rendered(self):
        """verify that the fields are not hightlighted and the message about
        shared reports is not included in the response for a project
        without sisters.
        """

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        self.assertNotContains(response, 'id="shared-milestone-message"')
        self.assertNotContains(response, 'class="fileinput shared"')

    def test_upload_report_sister_projects(self):
        """verify that we can upload more than 1 file"""

        # set up the sister relationship:
        self.project1.add_sister(self.project2.slug)

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        form_data = {
            "form-TOTAL_FORMS": 4,
            "form-INITIAL_FORMS": 0,
            # form 0 and 1 are used for proposal and completion reports
            "form-2-report_path": self.mock_file0,
        }

        self.client.post(url, form_data)

        # verify that the report was added to the Report table:
        report_count = Report.objects.all().count()
        self.assertEqual(report_count, 1)

        filepath = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file0.name)[1]
        ).replace("\\", "/")

        reports = self.project1.get_uploaded_reports()
        self.assertEqual(reports.values()[0]["report_path"], filepath)

        # make sure that the milestone is what we think it is:
        pr = ProjectMilestones.objects.filter(report=reports.select_related()[0])
        self.assertEqual(pr[0].milestone, self.rep2)
        self.assertEqual(pr[1].milestone, self.rep2)

        # verify that a link to the file is on the project details page
        url = reverse("project_detail", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath,)),
            filepath,
        )

        self.assertContains(response, linkstring)

        # ============================
        # verify all of the same details for the sister project

        reports = self.project2.get_uploaded_reports()
        self.assertEqual(reports.values()[0]["report_path"], filepath)

        # verify that a link to the file is on the project details page
        url = reverse("project_detail", args=(self.project2.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath,)),
            filepath,
        )
        self.assertContains(response, linkstring)

        # ============================
        # the information should not be associated with the thrid project
        reports = self.project3.get_uploaded_reports()
        self.assertEqual(reports.count(), 0)

    def test_upload_multiple_reports_to_sister_projects(self):
        """verify that we can upload more than 1 file"""

        # set up the sister relationship:
        self.project1.add_sister(self.project2.slug)

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)
        url = reverse("ReportUpload", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/UploadReports.html")

        form_data = {
            "form-TOTAL_FORMS": 3,
            "form-INITIAL_FORMS": 3,
            "form-0-report_path": self.mock_file0,  # Prop. Pres.
            "form-1-report_path": self.mock_file1,  # Proj. Completion
            "form-2-report_path": self.mock_file2,  # Summary Report
        }

        # submit the report
        self.client.post(url, form_data)

        # get the all of the reports and the proejct-reports assocaited
        # with this project
        reports = Report.objects.all()

        # verify that three reports have been added to the Report table:
        self.assertEqual(reports.count(), 3)

        # first file:
        filepath1 = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file0.name)[1]
        ).replace("\\", "/")

        self.assertEqual(reports.values()[0]["report_path"], filepath1)

        # make sure that the milestone is what we think it is: there
        # should TWO projectreport records associate with this report -
        # one for each sister project, and its report type should match
        # that of rep1
        pr = reports[0].projectreport.all()
        self.assertEqual(pr.count(), 2)

        self.assertQuerysetEqual(
            pr,
            [self.project1.prj_cd, self.project2.prj_cd],
            lambda a: a.project.prj_cd,
            ordered=False,
        )

        self.assertEqual(pr[0].milestone, self.rep0)

        # =============
        # second file:
        filepath2 = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file1.name)[1]
        ).replace("\\", "/")
        self.assertEqual(reports.values()[1]["report_path"], filepath2)
        report_id = reports.values_list()[1][0]

        # make sure that the milestone is what we think it is:
        # there should only be one projectreport record associate with
        # this report, and its report type should match that of rep1
        pr = ProjectMilestones.objects.filter(report__id=report_id)
        self.assertEqual(pr.count(), 1)
        # we skipped a file on the form - this should be associated
        # with the 3rd milestone
        self.assertEqual(pr[0].milestone, self.rep1)

        # =============
        # third file:
        filepath3 = os.path.join(
            UPLOAD_TO, os.path.split(self.mock_file2.name)[1]
        ).replace("\\", "/")

        self.assertEqual(reports.values()[2]["report_path"], filepath3)
        report_id = reports.values_list()[2][0]

        # make sure that the milestone is what we think it is:
        # there should TWO projectreport record associate with
        # this report, and its report type should be a completion report
        pr = ProjectMilestones.objects.filter(report__id=report_id)
        self.assertEqual(pr.count(), 2)
        self.assertQuerysetEqual(
            pr,
            [self.project1.prj_cd, self.project2.prj_cd],
            lambda a: a.project.prj_cd,
            ordered=False,
        )

        self.assertEqual(pr[0].milestone, self.rep2)

        # =============
        # verify that a links to each of the file are on
        # the details page for the first project
        url = reverse("project_detail", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath1,)),
            filepath1,
        )
        self.assertContains(response, linkstring)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath2,)),
            filepath2,
        )
        self.assertContains(response, linkstring)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath3,)),
            filepath3,
        )
        self.assertContains(response, linkstring)

        # the sister proejct should have the project proposal and
        # summary report, but not the completion report
        url = reverse("project_detail", args=(self.project2.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath1,)),
            filepath1,
        )
        self.assertContains(response, linkstring)

        # DOES NOT CONTAIN
        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath2,)),
            filepath2,
        )
        self.assertNotContains(response, linkstring)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath3,)),
            filepath3,
        )
        self.assertContains(response, linkstring)

        # ============================
        # the information should not be associated with the thrid project
        reports = self.project3.get_uploaded_reports()
        self.assertEqual(reports.count(), 0)

        url = reverse("project_detail", args=(self.project3.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath1,)),
            filepath1,
        )
        self.assertNotContains(response, linkstring)

        # DOES NOT CONTAIN
        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath2,)),
            filepath2,
        )
        self.assertNotContains(response, linkstring)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("serve_file", args=(filepath3,)),
            filepath3,
        )
        self.assertNotContains(response, linkstring)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.user.delete()
        self.rep0.delete()
        self.rep1.delete()
        self.rep2.delete()

        # finally get rid of the temporary file if it was created in
        # this test
        # mock_file0

        filepath = os.path.join(
            settings.MEDIA_ROOT, UPLOAD_TO, os.path.split(self.mock_file0.name)[1]
        )
        try:
            os.remove(filepath)
        except:
            pass

        # mock_file1
        filepath = os.path.join(
            settings.MEDIA_ROOT, UPLOAD_TO, os.path.split(self.mock_file1.name)[1]
        )
        try:
            os.remove(filepath)
        except:
            pass

        # mock_file2
        filepath = os.path.join(
            settings.MEDIA_ROOT, UPLOAD_TO, os.path.split(self.mock_file2.name)[1]
        )
        try:
            os.remove(filepath)
        except:
            pass

        # finally, clean out any test files that may have been
        # duplicates and named slightly differently than the others.
        media_dir = os.path.join(settings.MEDIA_ROOT, UPLOAD_TO)
        pattern = r"fake_test_file.*\.txt"
        files = [f for f in os.listdir(media_dir) if re.match(pattern, f)]

        for fname in files:
            filepath = os.path.join(settings.MEDIA_ROOT, UPLOAD_TO, fname)
            try:
                os.remove(filepath)
            except:
                pass


##  class FileDownloadTestCase(TestCase):
##
##
##      def setUp(self):
##          #USER
##          self.user = UserFactory.create(username = 'hsimpson',
##                                  first_name = 'Homer',
##                                  last_name = 'Simpson')
##
##          #required reports
##          self.rep0 = MilestoneFactory.create(label = "Proposal Presentation",
##                                  category = 'Core', order = 1)
##
##          #PROJECTS
##          self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111",
# 3                     owner=self.user)
##
##          #here is fake file that we will upload
##          self.mock_file = StringIO('GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00'
##                       '\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
##          self.mock_file.name = "path/to/some/fake/file.txt"
##
##
##
##      def tearDown(self):
##          self.project.delete()
##          self.user.delete()
##          self.rep.delete()
##
##          #finally get rid of the temporary file if it was created in
##          #this test
##          #mock_file0
##          filepath = os.path.join(settings.MEDIA_ROOT, settings.MEDIA_URL,
##                                  os.path.split(self.mock_file.name)[1])
##          try:
##              os.remove(filepath)
##          except:
##              pass


class TestServeMissingFile(TestCase):
    """
    If we try serve a file that does exists, we should get help error message.
    """

    def test_serve_missing_file(self):
        """
        If we try serve a file that does exists, we should get help
        error message.
        """

        missingfile = "MissingFile.doc"
        url = reverse("serve_file", args=(missingfile,))

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/MissingFile.html")
        self.assertContains(response, missingfile)

        msg = """<p>This is embarrassing.  I can't seem the find a file
        named "{}". It is possible that the file has been moved,
        renamed or deleted.</p>"""
        self.assertContains(response, msg.format(missingfile), html=True)
