from django.urls import reverse

#
from django.db.models.signals import pre_save, post_save
from django_webtest import WebTest

from pjtk2.models import send_notice_prjms_changed, ProjectMilestones, Project

# from testfixtures import compare
from pjtk2.tests.factories import (
    UserFactory,
    LakeFactory,
    ProjTypeFactory,
    ProjProtocolFactory,
    ProjectFactory,
    MilestoneFactory,
)

import pytest


@pytest.fixture(scope="module", autouse=True)
def disconnect_signals():
    """disconnect the signals before each test - not needed here"""
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)


##def setup():
##    '''disconnect the signals before each test - not needed here'''
##    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)
##
##
##def teardown():
##    '''re-connecct the signals here.'''
##    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)
##


class SisterFormTestCase(WebTest):
    def setUp(self):
        """we will need three projects with easy to rember project codes"""
        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        self.lake0 = LakeFactory(abbrev="HU", lake_name="Lake Huron")
        self.lake1 = LakeFactory(abbrev="ON", lake_name="Lake Ontario")

        self.ProjType = ProjTypeFactory()
        self.ProjType2 = ProjTypeFactory(project_type="Nearshore Index")

        # add in protocols here - differnt protocols cannot be sisters

        self.protocol0 = ProjProtocolFactory(
            protocol="Fall Walleye Index Netting", abbrev="FWIN"
        )
        self.protocol1 = ProjProtocolFactory(
            protocol="Broad Scale Monitoring", abbrev="BSM"
        )

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

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

        # same project type, but not approved
        self.project4 = ProjectFactory.create(
            prj_cd="LHA_IA12_444",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        # approved, different project type
        self.project5 = ProjectFactory.create(
            prj_cd="LHA_IA12_555",
            owner=self.user,
            project_type=self.ProjType2,
            lake=self.lake0,
            protocol=self.protocol1,
        )
        # approved, same project type, different year
        self.project6 = ProjectFactory.create(
            prj_cd="LHA_IA11_666",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake0,
            protocol=self.protocol1,
        )

        # different lake - should never be eligible
        self.project7 = ProjectFactory.create(
            prj_cd="LOA_IA12_999",
            owner=self.user,
            project_type=self.ProjType,
            lake=self.lake1,
            protocol=self.protocol1,
        )

        self.project0.approve()
        self.project1.approve()
        self.project2.approve()
        self.project3.approve()
        # self.project4.approve()
        self.project5.approve()
        self.project6.approve()
        self.project7.approve()

    def test_sisterbtn(self):
        """from the details pages, verify that the sisters button
        works and takes us to the sister project page for this
        project."""

        url = reverse("project_detail", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        # verify that the sister projects button exists
        linkstring = '<a href="%s"' % reverse(
            "SisterProjects", args=(self.project1.slug,)
        )
        self.assertContains(response, linkstring)

        response = response.click("Sister Projects")

        # if we click on it, verify that we are re-directed to the correct page
        # 'SisterProjects.html' (for this project)
        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        # verify that the page contains:
        # "Sister projects for:"
        self.assertContains(response, "Sister projects for:")
        # and self.project1.prj_cd
        self.assertContains(response, self.project1.prj_cd)

    def test_sisterlist_nosisters(self):
        """the sister project page for a project with two candidates, none
        selected."""
        # starting out at the sister project page for project1

        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        assert "Sister projects for:" in response

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project2.slug,)),
            self.project2.prj_cd,
        )

        assert linkstring in response
        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project3.slug,)),
            self.project3.prj_cd,
        )
        assert linkstring in response

        form = response.forms["sisterformset"]
        # there should be two forms in the formset (these form elements
        # end with -sister)
        fldcnt = [x for x in form.fields.keys() if x is not None]
        formcnt = len([x for x in fldcnt if x.endswith("-sister")])
        # formcnt = len([x for x in form.fields.keys() if x.endswith("-sister")])

        self.assertEqual(formcnt, 2)

        # the check boxes in both should == None
        self.assertEqual(form.fields["form-0-sister"][0].value, None)
        self.assertEqual(form.fields["form-1-sister"][0].value, None)

        # make sure that the projects that should be candidates or
        # sisters aren't in the response
        self.assertNotIn(self.project0.prj_cd, response)
        self.assertNotIn(self.project4.prj_cd, response)
        self.assertNotIn(self.project5.prj_cd, response)
        self.assertNotIn(self.project6.prj_cd, response)
        self.assertNotIn(self.project7.prj_cd, response)

    def test_sisterlist_onesister(self):
        """the sister project page for a project with one candidate,
        one sister already selected."""

        self.project1.add_sister(self.project2.slug)

        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        assert "Sister projects for:" in response

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project2.slug,)),
            self.project2.prj_cd,
        )

        assert linkstring in response
        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project3.slug,)),
            self.project3.prj_cd,
        )
        assert linkstring in response

        form = response.forms["sisterformset"]
        # there should be two forms in the formset (these form elements
        # end with -sister)
        fldcnt = [x for x in form.fields.keys() if x is not None]
        formcnt = len([x for x in fldcnt if x.endswith("-sister")])
        # formcnt = len([x for x in form.fields.keys() if x.endswith("-sister")])

        self.assertEqual(formcnt, 2)

        # the check boxes in both should == None
        self.assertEqual(form.fields["form-0-sister"][0].value, "on")
        self.assertEqual(form.fields["form-1-sister"][0].value, None)

        # make sure that the projects that should be candidates or
        # sisters aren't in the response
        self.assertNotIn(self.project0.prj_cd, response)
        self.assertNotIn(self.project4.prj_cd, response)
        self.assertNotIn(self.project5.prj_cd, response)
        self.assertNotIn(self.project6.prj_cd, response)

    def test_sisterlist_nocandidates(self):
        """the sister project page for a project without any
        candidates should not produce a form, but should present a
        meaningful message noting that there are no candidates
        currenly.  This test cases runs through scenarios with an
        unapproved project, a project of a differnt type and a project
        in a different year."""

        url = reverse("SisterProjects", args=(self.project4.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        # assert "Sister projects for:" in response
        self.assertContains(response, "Sister projects for:")

        msg = "There are currently no comperable projects for %s" % self.project4.prj_cd
        self.assertIn(msg, response)

        # make sure that the projects that should not be candidates or
        # sisters aren't in the response
        self.assertNotIn(self.project0.prj_cd, response)
        self.assertNotIn(self.project1.prj_cd, response)
        self.assertNotIn(self.project2.prj_cd, response)
        self.assertNotIn(self.project3.prj_cd, response)
        self.assertNotIn(self.project5.prj_cd, response)
        self.assertNotIn(self.project6.prj_cd, response)
        self.assertNotIn(self.project7.prj_cd, response)

        # Differnt Project Type
        url = reverse("SisterProjects", args=(self.project5.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        assert "Sister projects for:" in response

        msg = "There are currently no comperable projects for %s" % self.project5.prj_cd
        self.assertIn(msg, response)

        # make sure that the projects that should not be candidates or
        # sisters aren't in the response
        self.assertNotIn(self.project0.prj_cd, response)
        self.assertNotIn(self.project1.prj_cd, response)
        self.assertNotIn(self.project2.prj_cd, response)
        self.assertNotIn(self.project3.prj_cd, response)
        self.assertNotIn(self.project4.prj_cd, response)
        self.assertNotIn(self.project6.prj_cd, response)
        self.assertNotIn(self.project7.prj_cd, response)

        # approved project, different year
        url = reverse("SisterProjects", args=(self.project6.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        assert "Sister projects for:" in response

        msg = "There are currently no comperable projects for %s" % self.project6.prj_cd
        self.assertIn(msg, response)

        # make sure that the projects that should not be candidates or
        # sisters aren't in the response
        self.assertNotIn(self.project0.prj_cd, response)
        self.assertNotIn(self.project1.prj_cd, response)
        self.assertNotIn(self.project2.prj_cd, response)
        self.assertNotIn(self.project3.prj_cd, response)
        self.assertNotIn(self.project4.prj_cd, response)
        self.assertNotIn(self.project5.prj_cd, response)
        self.assertNotIn(self.project7.prj_cd, response)

    def test_add_remove_sisters(self):
        """this test will test the whole process.  We will log into
        the sister list, click on a sister, submit the form, return to
        the sister page, verify that the sister is selected, unselect
        it and re-sumbit the form.  Finally retrun to the list of
        sisters and verify that no sisters are selected."""

        # we will log into the lister list, click on a sister,
        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")
        form = response.forms["sisterformset"]
        # there should be two forms in the formset (these form elements
        # end with -sister)

        fldcnt = [x for x in form.fields.keys() if x is not None]
        formcnt = len([x for x in fldcnt if x.endswith("-sister")])

        self.assertEqual(formcnt, 2)

        # the check boxes in both should == None
        self.assertEqual(form.fields["form-0-sister"][0].value, None)
        self.assertEqual(form.fields["form-1-sister"][0].value, None)

        # check one of the boxes and submit the form,
        form.fields["form-0-sister"][0].value = "on"

        form.submit()

        proj = Project.objects.get(slug=self.project1.slug)
        sisters = proj.get_sisters()
        self.assertEqual(len(sisters), 1)
        self.assertEqual(sisters[0].prj_cd, self.project2.prj_cd)

        # ========================
        # return to the sister page,
        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)
        assert response.status_int == 200

        form = response.forms["sisterformset"]

        # verify that the sister is selected,
        self.assertEqual(form.fields["form-0-sister"][0].value, "on")
        self.assertEqual(form.fields["form-1-sister"][0].value, None)

        # unselect it and re-sumbit the form.
        form.fields["form-0-sister"][0].value = None
        form.submit()

        proj = Project.objects.get(slug=self.project1.slug)
        sisters = proj.get_sisters()
        self.assertEqual(len(sisters), 0)

        # ========================
        # retuRn to the list of sisters one final time and verify that
        # no sisters are selected

        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")
        form = response.forms["sisterformset"]
        # there should be two forms in the formset (these form elements
        # end with -sister)
        fldcnt = [x for x in form.fields.keys() if x is not None]
        formcnt = len([x for x in fldcnt if x.endswith("-sister")])
        # formcnt = len([x for x in form.fields.keys() if x.endswith("-sister")])

        self.assertEqual(formcnt, 2)

        # the check boxes in both should == None
        self.assertEqual(form.fields["form-0-sister"][0].value, None)
        self.assertEqual(form.fields["form-1-sister"][0].value, None)

    def test_sisterlist_deletesister(self):
        """this simply verifies that we can delete a single sister,
        leaving the family and remaining sisters intact."""

        # start out with a family of three:
        self.project1.add_sister(self.project2.slug)
        self.project1.add_sister(self.project3.slug)

        # verify that the project 1 has the sisters we think:
        sisters1 = self.project1.get_sisters()
        prj_cds = [x.prj_cd for x in sisters1]
        # use sets - order doesn't matter
        self.assertEqual(
            set(prj_cds), set([self.project2.prj_cd, self.project3.prj_cd])
        )

        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        assert "Sister projects for:" in response

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project2.slug,)),
            self.project2.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

        linkstring = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project3.slug,)),
            self.project3.prj_cd,
        )
        self.assertContains(response, linkstring, html=True)

        form = response.forms["sisterformset"]
        # there should be two forms in the formset (these form elements
        # end with -sister)
        fldcnt = [x for x in form.fields.keys() if x is not None]
        formcnt = len([x for x in fldcnt if x.endswith("-sister")])
        # formcnt = len([x for x in form.fields.keys() if x.endswith("-sister")])

        self.assertEqual(formcnt, 2)

        # the check boxes in both should == None
        self.assertEqual(form.fields["form-0-sister"][0].value, "on")
        self.assertEqual(form.fields["form-1-sister"][0].value, "on")

        # make sure that the projects that should be candidates or
        # sisters aren't in the response
        self.assertNotIn(self.project0.prj_cd, response)
        self.assertNotIn(self.project4.prj_cd, response)
        self.assertNotIn(self.project5.prj_cd, response)
        self.assertNotIn(self.project6.prj_cd, response)
        self.assertNotIn(self.project7.prj_cd, response)

        # resubmit the form the check boxe corresponding to LAH_IA12_333 unchecked:
        html_id = "form-{}-sister".format(prj_cds.index("LHA_IA12_333"))
        form.fields[html_id][0].value = None

        form.submit()

        # project at index [0] shouldn't have any sisters now
        sisters = self.project1.get_sisters()
        self.assertEqual(len(sisters), 1)
        self.assertEqual(sisters[0].prj_cd, self.project2.prj_cd)

        # project at index [0] shouldn't have any sisters now
        self.assertEqual(len(self.project3.get_sisters()), 0)

    def test_disown_sister(self):
        """This is case where we actuall want to remove the current
        project from the family - rather than going to a sister page
        an unselecting this project, we choose to unselect all of the
        current sisters."""

        self.project1.add_sister(self.project2.slug)
        self.project1.add_sister(self.project3.slug)

        proj = Project.objects.get(slug=self.project1.slug)
        sisters = proj.get_sisters()
        self.assertEqual(len(sisters), 2)
        self.assertEqual(sisters[0].prj_cd, self.project2.prj_cd)
        self.assertEqual(sisters[1].prj_cd, self.project3.prj_cd)

        # we will log into the lister list, click on a sister,
        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.app.get(url, user=self.user)

        assert response.status_int == 200
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")
        form = response.forms["sisterformset"]
        # there should be two forms in the formset
        fldcnt = [x for x in form.fields.keys() if x is not None]
        formcnt = len([x for x in fldcnt if x.endswith("-sister")])
        # formcnt = len([x for x in form.fields.keys() if x.endswith("-sister")])

        self.assertEqual(formcnt, 2)

        # the check boxes in both should == None
        self.assertEqual(form.fields["form-0-sister"][0].value, "on")
        self.assertEqual(form.fields["form-1-sister"][0].value, "on")

        # uncheck both of the boxes and submit the form,
        form.fields["form-0-sister"][0].value = None
        form.fields["form-1-sister"][0].value = None
        form.submit()

        # project 1 shouldn't have any sisters now
        proj = Project.objects.get(slug=self.project1.slug)
        sisters = proj.get_sisters()
        self.assertEqual(len(sisters), 0)

        # project 2 should have just one sister - project 3
        proj = Project.objects.get(slug=self.project2.slug)
        sisters = proj.get_sisters()
        self.assertEqual(len(sisters), 1)
        self.assertEqual(sisters[0].prj_cd, self.project3.prj_cd)

        # Likewise project 3 should have just one sister - project 2
        proj = Project.objects.get(slug=self.project3.slug)
        sisters = proj.get_sisters()
        self.assertEqual(len(sisters), 1)
        self.assertEqual(sisters[0].prj_cd, self.project2.prj_cd)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.user.delete()


class SisterProjectsTestCase(WebTest):
    """Verify that the user can see and update sisters associated with
    projects"""

    def setUp(self):
        """we will need three projects with easy to rember project codes"""
        self.user = UserFactory(
            username="hsimpson", first_name="Homer", last_name="Simpson"
        )

        # create milestones
        self.milestone1 = MilestoneFactory.create(
            label="Approved", category="Core", order=1, report=False
        )
        self.milestone2 = MilestoneFactory.create(
            label="Sign off", category="Core", order=999, report=False
        )

        self.ProjType = ProjTypeFactory()
        self.ProjType2 = ProjTypeFactory(project_type="Nearshore Index")

        self.project1 = ProjectFactory.create(
            prj_cd="LHA_IA12_111", owner=self.user, project_type=self.ProjType
        )

        self.project2 = ProjectFactory.create(
            prj_cd="LHA_IA12_222", owner=self.user, project_type=self.ProjType
        )

        self.project3 = ProjectFactory.create(
            prj_cd="LHA_IA12_333",
            prj_nm="another fake project",
            owner=self.user,
            project_type=self.ProjType,
        )
        # don't forget to approve the projects
        self.project1.approve()
        self.project2.approve()
        self.project3.approve()

    def test_sisterbtn(self):

        login = self.client.login(username=self.user.username, password="Abcd1234")
        self.assertTrue(login)

        url = reverse("SisterProjects", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/SisterProjects.html")

        linktext = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project2.slug,)),
            self.project2.prj_cd,
        )
        self.assertContains(response, linktext)

    def test_detail_contains_link_to_sister(self):
        """if the project has a sister, a link to that sister should appear on
        the detail page for that project."""

        # set up the sister relationship
        self.project1.add_sister(self.project2.slug)

        url = reverse("project_detail", args=(self.project1.slug,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pjtk2/projectdetail.html")

        self.assertContains(response, "Sister Projects:")
        self.assertContains(response, self.project2.prj_nm)
        linktext = '<a href="%s">%s</a>' % (
            reverse("project_detail", args=(self.project2.slug,)),
            self.project2.prj_cd,
        )
        self.assertContains(response, linktext)

        self.assertNotContains(response, self.project3.prj_cd)
        self.assertNotContains(response, self.project3.prj_nm)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.user.delete()
