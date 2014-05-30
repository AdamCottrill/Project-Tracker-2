from django.test import TestCase
from django.db.models.signals import pre_save, post_save
from pjtk2.models import *
from pjtk2.tests.factories import *

from pjtk2.functions import get_minions, get_supervisors

import datetime
import pytz
import pdb
import sys

import pytest

@pytest.fixture(scope="module", autouse=True)
def disconnect_signals():
    '''disconnect the signals before each test - not needed here'''
    pre_save.disconnect(send_notice_prjms_changed, sender=ProjectMilestones)

def print_err(*args):
    sys.stderr.write(' '.join(map(str,args)) + '\n')



class TestProjectApproveUnapproveMethods(TestCase):
    '''Project instances have been given class methods to approve,
    rove and sign off.  These tests verify that they work as
    expected.
    '''

    def setUp(self):
        '''we will need three projects with easy to rember project codes'''

        import os
        print "os.environ['DJANGO_SETTINGS_MODULE'] = %s" % os.environ['DJANGO_SETTINGS_MODULE']


        self.user = UserFactory(username = 'hsimpson',
                                first_name = 'Homer',
                                last_name = 'Simpson')
        
        #Add milestones
        self.milestone1 = MilestoneFactory.create(label="Approved",
                                             category = 'Core', order=1, 
                                             report=False)
        self.milestone2 = MilestoneFactory.create(label="Completed",
                                        category = 'Core', order=2, 
                                             report=False)
        self.milestone3 = MilestoneFactory.create(label="Sign off",
                                        category = 'Core', order=999, 
                                             report=False)
        
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", 
                                              owner=self.user)

    def test_approve_unapprove_project(self):

        #verify that the project milestone for this project is null
        #before we call the method
        milestone = ProjectMilestones.objects.get(
                             project=self.project1, 
                             milestone__label='Approved')
        self.assertIsNone(milestone.completed)

        #call self.project1.approve()
        self.project1.approve()

        #assert that the value in completed is not null and that it is
        #close to the current time
        now = datetime.datetime.now(pytz.utc)
        milestone = ProjectMilestones.objects.get(
                             project=self.project1, 
                             milestone__label='Approved')
        completed = milestone.completed
        self.assertIsNotNone(completed)
        self.assertTrue((completed - now)<datetime.timedelta(seconds=1))


        #call self.project1.unapprove()
        self.project1.unapprove()
        #assert that the value in completed is null
        milestone = ProjectMilestones.objects.get(
                             project=self.project1, 
                             milestone__label='Approved')
        completed = milestone.completed
        self.assertIsNone(completed)


    def test_signoff_project(self):

        #verify that the 'Sign off' project milestone for this project is null
        #before we call the method

        #assert that the value in completed is not null and that it is
        #close to the current time

        milestone = ProjectMilestones.objects.get(
                             project=self.project1, 
                             milestone__label='Sign off')
        self.assertIsNone(milestone.completed)

        #call self.project1.approve()
        #call self.project1.signoff()
        self.project1.signoff()

        #assert that the value in completed is not null and that it is
        #close to the current time
        now = datetime.datetime.now(pytz.utc)
        milestone = ProjectMilestones.objects.get(
                             project=self.project1, 
                             milestone__label='Sign off')
        completed = milestone.completed
        self.assertIsNotNone(completed)
        self.assertTrue((completed - now)<datetime.timedelta(seconds=1))

    def tearDown(self):

        self.project1.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.milestone3.delete()
        self.user.delete()


class TestProjectModel(TestCase):

    def setUp(self):

        self.user = UserFactory(username = 'hsimpson',
                                first_name = 'Homer',
                                last_name = 'Simpson')

        #self.employee = EmployeeFactory(user=self.user) 

        #define these as strings here so that we can access them later
        #and verify that the returned values match.
        self.commentStr = "This is a fake comment."
        self.ProjectName = "Homer's Odyssey"
        
        #we need to create some models with different years - starting
        #with the current year.
        yr = datetime.datetime.now()
        prj_cd = "LHA_IA%s_111" % str(yr.year)[-2:]
        self.project1 = ProjectFactory.create(prj_cd=prj_cd,
                                              owner=self.user,
                                              comment=self.commentStr,
                                              prj_nm = self.ProjectName)

        prj_cd = "LHA_IA%s_222" % str(yr.year -1)[-2:]
        self.project2 = ProjectFactory.create(prj_cd=prj_cd,
                                              owner=self.user)

        prj_cd = "LHA_IA%s_333" % str(yr.year-2)[-2:]
        self.project3 = ProjectFactory.create(prj_cd=prj_cd,
                                              owner=self.user)


    def test_project_unicode(self):
        """make sure that the string representation of our project is
        what we expect (project name (project code))"""

        should_be = "%s (%s)" % (self.project1.prj_nm, 
                                 self.project1.prj_cd)
        self.assertEqual(str(self.project1), should_be)                


    def test_project_description(self):
        '''verify that project description is return properly.'''

        self.assertEqual(self.project1.description(), 
                         self.commentStr)                


    def test_project_name(self):
        '''verify that project name is return properly.'''

        self.assertEqual(self.project1.name(), 
                         self.ProjectName)                



    def test_project_suffix(self):
        '''verify that project suffix is the last three elements of
        the project code'''

        self.assertEqual(len(self.project1.project_suffix()), 3)                
        should_be = self.project1.prj_cd[-3:]
        self.assertEqual(self.project1.project_suffix(), should_be)                


    def test_project_save(self):
        '''verify that the fields populated on save are what they
        should be'''
        prj_cd = "LHA_IA12_111"
        prj_nm = "Fake Project"
        project = ProjectFactory.create(prj_cd = prj_cd)

        project.save()
        should_be = prj_cd.lower()
        self.assertEqual(project.slug, should_be)
        should_be = "20" + prj_cd[6:8]                
        self.assertEqual(str(project.year), should_be)                


    def test_projects_this_year(self):
        '''This one should return self.project1, but not project 2 or 3'''
        projects = Project.this_year.all()
        self.assertEqual(projects.count(),1)
        self.assertEqual(projects[0].prj_cd, self.project1.prj_cd)

    def test_projects_last_year(self):
        '''This one should return self.project2, but not project 1 or 3'''
        projects = Project.last_year.all()
        self.assertEqual(projects.count(),1)
        self.assertEqual(projects[0].prj_cd, self.project2.prj_cd)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()
        self.user.delete()


class TestMilestoneModel(TestCase):        

    def setUp(self):

        self.core1 = MilestoneFactory.create(label="core1",
                                             category = 'Core', order=1, 
                                             report=True)
        self.core2 = MilestoneFactory.create(label="core2",
                                        category = 'Core', order=2, 
                                             report=True)
        self.core3 = MilestoneFactory.create(label="core3",
                                        category = 'Core', order=3, 
                                             report=True)
        self.custom = MilestoneFactory.create(label="custom",
                                        category = 'Custom', order=50, 
                                              report=True)

        self.milestone1 = MilestoneFactory.create(label="Approved",
                                             category = 'Core', order=1, 
                                             report=False)
        self.milestone2 = MilestoneFactory.create(label="Completed",
                                        category = 'Core', order=2, 
                                             report=False)
        self.milestone3 = MilestoneFactory.create(label="Signoff",
                                        category = 'Core', order=999, 
                                             report=False)
        self.customMS = MilestoneFactory.create(label="Aging",
                                        category = 'Custom', order=50, 
                                              report=False)

                                            
        self.project = ProjectFactory.create()


    def test_initial_reports_on_save_method(self):
        '''A record should be made automatically for each core report
        when a new project is created.'''
        # make some fake reports, the three core reports should be
        # automatically associated with a new project, and verify that
        # the custom report is not when the project is created.
                
        myreports = ProjectMilestones.objects.filter(project=self.project,
                                                     milestone__report=True)
        self.assertEqual(myreports.count(), 3)

        outstanding = self.project.get_outstanding()
        self.assertEqual(outstanding.count(), 3)

    def test_get_assigment_methods(self):

        assignments = self.project.get_reporting_requirements()
        cnt = assignments.count()
        self.assertEqual(cnt, 3)
        
        self.assertEqual(self.project.get_core_assignments().count(), 3)
        self.assertEqual(self.project.get_custom_assignments().count(), 0)
        
        #we haven't uploaded any reports, so this should be 0
        self.assertEqual(self.project.get_complete().count(), 0)


    def test_get_milestones(self):
        '''by default, all core milestones are associated with project'''

        milestones = self.project.get_milestones()
        cnt = milestones.count()
        self.assertEqual(cnt, 3)
        self.assertNotEqual(cnt, 2)
        self.assertNotEqual(cnt, 4)
        
        #verify that the labels of my milestones appear in the correct order
        shouldbe = ['Approved','Completed','Signoff']

        self.assertQuerysetEqual(
            milestones,['Approved','Completed','Signoff'],
            lambda a:a.milestone.label
            )

        #add the custom milestone to this project
        ProjectMilestones.objects.create(project=self.project, 
                                         milestone=self.customMS)
        #verify that it appears in the milestone list for this project
        milestones = self.project.get_milestones()
        cnt = milestones.count()

        self.assertEqual(cnt, 4)
        self.assertQuerysetEqual(
            milestones,['Approved','Completed', 'Aging','Signoff'],
            lambda a:a.milestone.label
            )

        #we changed our mind an aging is no longer required:
        ProjectMilestones.objects.filter(project=self.project, 
                                         milestone=self.customMS).update(
                                             required=False)

        milestones = self.project.get_milestones()
        cnt = milestones.count()

        self.assertEqual(cnt, 3)
        self.assertQuerysetEqual(
            milestones,['Approved','Completed','Signoff'],
            lambda a:a.milestone.label
            )


    def test_get_assigment_dicts(self):
        
        #dict = self.project.get_assignment_dicts()
        dict = self.project.get_milestone_dicts()
        print "dict.core = %s" % dict['Core']
        print "dict.custom = %s" % dict['Custom']

        core = dict['Core']

        should_be = [self.core1.id, self.core2.id, self.core3.id]
        self.assertEqual(core['assigned'], should_be)

        reports = [str(x[1]) for x in core['milestones']]
        self.assertEqual(reports,[self.core1.label, 
                                      self.core2.label, 
                                      self.core3.label])

        custom = dict['Custom']
        self.assertEqual(custom['assigned'],[])
        reports = [str(x[1]) for x in custom['milestones']]
        self.assertEqual(reports,[self.custom.label])

    def test_get_assigment_methods_w_custom_report(self): 

        '''verify that custom reports are can be added and retrieved
        as expected.'''

        custom1 = MilestoneFactory.create(label="custom1", report=True, 
                                          category = 'Custom', order=99)

        projectreport = ProjectMilestonesFactory(project=self.project,
                                             milestone=custom1)
        
        self.assertEqual(self.project.get_reporting_requirements().count(), 4)
        self.assertNotEqual(self.project.get_reporting_requirements().count(), 3)
        self.assertNotEqual(self.project.get_reporting_requirements().count(), 5)
        
        self.assertEqual(self.project.get_core_assignments().count(), 3)
        self.assertEqual(self.project.get_custom_assignments().count(), 1)

        report = self.project.get_custom_assignments()[0]
        self.assertEqual(report.required, True)
        self.assertEqual(str(report.milestone), 'custom1')
        
        #we haven't uploaded any reports, so this should be 0
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
    '''functions to test the models and methods assoicated with reports'''

    def setUp(self):

        #here are a couple of reports we will use, one will have a
        #report associated with it (complete), one will not (it will
        #be outstanding)
        self.core1 = MilestoneFactory.create(label="core1", report=True,
                                        category = 'Core', order=1)
        self.core2 = MilestoneFactory.create(label="core2", report = True,
                                        category = 'Core', order=2)

        self.project = ProjectFactory.create()

        #retrieve the projectreport that would have been created for
        #the new project
        self.projectreport = ProjectMilestones.objects.get(project=self.project,
                                                   milestone=self.core1)

        #create a fake report
        report = ReportFactory(report_path="path\to\fake\file.txt")
        #associate the report with the project reporting requirement
        report.projectreport.add(self.projectreport) 
        
    def test_get_reporting_requirementss(self):
        rep = self.project.get_uploaded_reports()
        self.assertEqual(len(rep),1)
        self.assertEqual(rep[0].report_path, "path\to\fake\file.txt")
        #self.fail("Finish this test.")

    def test_get_completed(self):
        '''a function to verify that the method to retrieve completed
        reporting requirements works.'''
        comp = self.project.get_complete()
        self.assertEqual(len(comp),1)

        #make sure that the project report objects match the attributes of core1 and self.project
        self.assertEqual(comp.values()[0]['required'], self.projectreport.required)
        self.assertEqual(comp.values()[0]['milestone_id'], 
                         self.projectreport.milestone_id)
        self.assertEqual(comp.values()[0]['project_id'], self.project.id) 

        #verify that core2 isnt in the completed list - it isn't done yet:
        projids = [x['milestone_id'] for x in comp.values()] 
        self.assertNotIn(self.core2.id, projids)

    def test_get_outstanding(self):
        '''a test to verify that the method to retrieve unfinished
        reporting requirements works.'''
        missing = self.project.get_outstanding()
        self.assertEqual(len(missing),1)

        #make sure that the project report objects match the
        #attributes of core2 and self.project
        self.assertEqual(missing.values()[0]['required'], 
                         self.projectreport.required)
        self.assertEqual(missing.values()[0]['milestone_id'], 
                         self.core2.id)
        self.assertEqual(missing.values()[0]['project_id'], self.project.id) 

        #verify that core1 isnt in the missing list - it was completed
        #during setup
        projids = [x['milestone_id'] for x in missing.values()] 
        self.assertNotIn(self.core1.id, projids)

    def tearDown(self):
        self.project.delete()
        self.projectreport.delete()


class TestModelSisters(TestCase):        
    '''make sure we can add and delete sisters to projects and that
    families are created and cleaned when not needed.'''

    def setUp(self):
        '''we will need three projects with easy to rember project codes'''

        self.user = UserFactory(username = 'hsimpson',
                                first_name = 'Homer',
                                last_name = 'Simpson')
        
        self.ProjType = ProjTypeFactory()
        self.ProjType2 = ProjTypeFactory(project_type = "Nearshore Index")
        

        #create milestones
        self.milestone1 = MilestoneFactory.create(label="Approved",
                                             category = 'Core', order=1, 
                                             report=False)
        self.milestone2 = MilestoneFactory.create(label="Sign off",
                                        category = 'Core', order=999, 
                                             report=False)

        #projects
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", 
                                              owner=self.user,
                                              project_type = self.ProjType)

        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222", 
                                              owner=self.user, 
                                              project_type = self.ProjType)

        self.project3 = ProjectFactory.create(prj_cd="LHA_IA12_333", 
                                              owner=self.user, 
                                              project_type = self.ProjType)

        self.project4 = ProjectFactory.create(prj_cd="LHA_IA12_444", 
                                              owner=self.user, 
                                              project_type = self.ProjType)

        self.project5 = ProjectFactory.create(prj_cd="LHA_IA12_555", 
                                              owner=self.user,
                                              project_type = self.ProjType2)

        self.project6 = ProjectFactory.create(prj_cd="LHA_IA11_666", 
                                              owner=self.user,
                                              project_type = self.ProjType) 

        self.project1.approve()
        self.project2.approve()
        self.project3.approve()
        #self.project4.approve()  - #4 Not Approved
        self.project5.approve()
        self.project6.approve()


    def test_sisters(self):

        #make sure that the family table is empty
        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt,0)

        self.assertEqual(self.project1.get_sisters(), [])
        self.assertEqual(self.project1.get_family(), None)

        candidates = self.project1.get_sister_candidates()
        self.assertEqual(candidates.count(), 2)
        
        #make project 1 and 2 sisters:
        self.project1.add_sister(self.project2.slug)

        #verify that they are sisters and have the same family
        sisters1 = self.project1.get_sisters()
        sisters2 = self.project2.get_sisters()
        #and there they each only have one candidate:
        candidates = self.project1.get_sister_candidates()
        self.assertEqual(candidates.count(), 1)
        candidates = self.project2.get_sister_candidates()
        self.assertEqual(candidates.count(), 1)

        #each sister should return the other:
        self.assertEqual(sisters1[0].prj_cd, "LHA_IA12_222")
        self.assertEqual(sisters2[0].prj_cd, "LHA_IA12_111")

        #and they should all be in the same family
        self.assertEqual(self.project1.get_family(), self.project2.get_family())
        #project3 should not have a family
        self.assertEqual(self.project3.get_family(), None)

        #make project3 a sistser of project2
        self.project2.add_sister(self.project3.slug)
        #automatically it should be a sister of project1
        sisters1 = self.project1.get_sisters()
        sisters2 = self.project2.get_sisters()
        sisters3 = self.project3.get_sisters()

        self.assertEqual(sisters1[0].prj_cd,"LHA_IA12_222")
        self.assertEqual(sisters1[1].prj_cd,"LHA_IA12_333")
        #self.assertEqual(sisters1[2].prj_cd,"LHA_IA12_333")

        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt, 1)

        #there shouldn't be any candidates - there all sisters now
        candidates = self.project1.get_sister_candidates()
        self.assertEqual(list(candidates), [])
        self.assertEqual(candidates.count(), 0)
        
        #remove project2 from the family
        self.project1.delete_sister(self.project2.slug)
        self.assertEqual(self.project2.get_sisters(), [])
        self.assertEqual(self.project2.get_family(), None)
        #self.assertEqual(self.project1.get_sisters(), self.project3.get_sisters())
        self.assertEqual(self.project1.get_family(), self.project3.get_family())

        #delete the last sister and verify that everything is empty
        self.project1.delete_sister(self.project3.slug)        
        self.assertEqual(self.project1.get_sisters(), [])
        self.assertEqual(self.project1.get_family(), None)
        self.assertEqual(self.project2.get_sisters(), [])
        self.assertEqual(self.project2.get_family(), None)
        self.assertEqual(self.project3.get_sisters(), [])
        self.assertEqual(self.project3.get_family(), None)

        #make sure that the family table is empty again
        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt,0)


    def test_sisters_include_self(self):

        #make sure that the family table is empty
        FamilyCnt = Family.objects.all().count()
        self.assertEqual(FamilyCnt,0)
        
        #make project 1 and 2 sisters:
        self.project1.add_sister(self.project2.slug)

        #verify that they are sisters and have the same family
        sisters1 = self.project1.get_sisters(False)
        sisters2 = self.project2.get_sisters(False)

        self.assertQuerysetEqual(
            sisters1,[self.project1.prj_cd, self.project2.prj_cd],
            lambda a:a.prj_cd
            )

        self.assertQuerysetEqual(
            sisters2,[self.project1.prj_cd, self.project2.prj_cd],
            lambda a:a.prj_cd
            )

    def test_has_sisters(self):
        """has_sisters() is a simple method of project objects.  Returns True
        if the object has one or more sisters, false otherwise.
        
        """
        #make project 1 and 2 sisters:
        self.project1.add_sister(self.project2.slug)

        self.assertTrue(self.project1.has_sister())
        self.assertTrue(self.project2.has_sister())
        #number three should not have any sisters
        self.assertFalse(self.project3.has_sister())        


    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()        
        self.project4.delete()        
        self.project5.delete()        
        self.project6.delete()        
        self.ProjType.delete()
        self.ProjType2.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.user.delete()
        

class TestModelBookmarks(TestCase):        
    '''Verify that the bookmark objects return the data in the
    expected format.'''

    def setUp(self):
        '''we will need three projects with easy to rember project
        codes'''

        self.user = UserFactory(username = 'hsimpson',
                                first_name = 'Homer',
                                last_name = 'Simpson')

        self.user2 = UserFactory(username = 'mburns',
                                first_name = 'Monty',
                                last_name = 'Burns')

        self.ProjType = ProjTypeFactory(project_type = "Nearshore Index")

        self.project = ProjectFactory.create(prj_cd="LHA_IA12_111", 
                                              project_type = self.ProjType)

    def test_BookmarkAttributes(self):
        '''Verify that bookmark methods retrun expected values'''
        bookmark = Bookmark.objects.create(user=self.user,
                                           project=self.project)

        self.assertEqual(bookmark.get_project_code(), self.project.prj_cd)
        self.assertEqual(bookmark.get_project_url(), 
                         self.project.get_absolute_url())
        self.assertEqual(bookmark.year(), self.project.year)
        self.assertEqual(str(bookmark), str(self.project))
        self.assertEqual(bookmark.name(), self.project.prj_nm)
        self.assertEqual(bookmark.project_type(), self.project.project_type)



    def test_bookmark_get_watchers_method(self):
        '''This function should return a list of users who are watching this
        project.  This function is need to help build the message
        distribution list
        '''

        #homer bookmarks this project
        bookmark = Bookmark.objects.create(user=self.user, 
                                           project=self.project)
        watchers = bookmark.get_watchers()
        self.assertEqual(watchers[0],self.user)

        #Mr Burns bookmarks this project too
        bookmark = Bookmark.objects.create(user=self.user2, 
                                           project=self.project)
        watchers = bookmark.get_watchers()

        self.assertEqual(watchers.sort(), [self.user, self.user2].sort())


    def tearDown(self):
        self.project.delete()
        self.ProjType.delete()
        self.user.delete()
        self.user2.delete()


class TestProjectTagging(TestCase):        
    '''make sure we can add and delete tags, and retrieve all projects
    associated with a given tag.'''

    def setUp(self):
        '''we will need three projects with easy to rember project codes'''

        self.user = UserFactory(username = 'hsimpson',
                                first_name = 'Homer',
                                last_name = 'Simpson')        
        
        
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", 
                                              owner=self.user)
        self.project2 = ProjectFactory.create(prj_cd="LHA_IA12_222",
                                              owner=self.user)
        self.project3 = ProjectFactory.create(prj_cd="LHA_IA12_333",
                                              owner=self.user)

    def test_add_remove_tags(self):
        '''verify that we can add and remove tags to a project'''
        self.assertEqual(len(self.project1.tags.all()),0)
        self.project1.tags.add("perch","walleye","whitefish")
        self.assertEqual(len(self.project1.tags.all()),3)
        
        tags = self.project1.tags.all()
        for tag in tags:
            self.assertTrue(str(tag) in ["perch","walleye","whitefish"])
        #assert 3==0

        self.project1.tags.remove("perch") 
        tags = self.project1.tags.all()
        self.assertEqual(tags.count(),2)
        for tag in tags:
            self.assertTrue(str(tag) in ["walleye","whitefish"])
        self.assertFalse("perch" in tags)

        self.project1.tags.clear()
        self.assertEqual(len(self.project1.tags.all()),0)

    def test_filter_projects_by_tags(self):
        '''verify that we can get projects with the same tag'''

        self.assertEqual(len(self.project1.tags.all()),0)
        self.project1.tags.add("project1","project12","allprojects")
        self.project2.tags.add("project2","project12","allprojects")
        self.project3.tags.add("project3","allprojects")

        projects = Project.objects.filter(tags__name__in=["allprojects"])
        self.assertEqual(projects.count(),3)
        self.assertQuerysetEqual(projects,
                                 [self.project1.prj_cd,
                                  self.project2.prj_cd,
                                  self.project3.prj_cd],
                                 lambda a:a.prj_cd)

        projects = Project.objects.filter(tags__name__in=["project12"])
        self.assertEqual(projects.count(),2)
        self.assertQuerysetEqual(projects,
                                 [self.project1.prj_cd,
                                  self.project2.prj_cd],
                                 lambda a:a.prj_cd)


        projects = Project.objects.filter(tags__name__in=["project1"])
        self.assertEqual(projects.count(),1)
        self.assertEqual(projects[0].prj_cd,self.project1.prj_cd)

    def tearDown(self):
        self.project1.delete()
        self.project2.delete()
        self.project3.delete()


class TestEmployeeFunctions(TestCase):
    
    def setUp(self):

        self.user1 = UserFactory(first_name = "Jerry", last_name="Seinfield",
                                username='jseinfield')

        self.user2 = UserFactory(first_name = "George", last_name="Costanza",
                                username='gcostanza')

        self.user3 = UserFactory(first_name = "Cosmo", last_name="Kramer",
                                username='ckramer')
        self.user4 = UserFactory(first_name = "Elaine", last_name="Benis",
                                username='ebenis')
        self.user5 = UserFactory(first_name = "Kenny", last_name="Banya",
                                username='kbanya')

        self.user6 = UserFactory(first_name = "Ruteger", last_name="Newm",
                                username='rnewman')


        #now setup employee relationships

        self.employee1 = EmployeeFactory(user=self.user1)
        self.employee2 = EmployeeFactory(user=self.user2, 
                                         supervisor=self.employee1)
        self.employee3 = EmployeeFactory(user=self.user3, 
                                         supervisor=self.employee1)
        self.employee4 = EmployeeFactory(user=self.user4, 
                                         supervisor=self.employee3)
        self.employee5 = EmployeeFactory(user=self.user5, 
                                         supervisor=self.employee3)
        self.employee6 = EmployeeFactory(user=self.user6, 
                                         supervisor=self.employee5)
        
        #Jerry is everyone's boss
        #Jerry's direct reports are George and Kramer
        #Elaine reports to Kramer
        #Banya reports to Kramer
        #Newman reports to Banya

    def test_get_supervisors(self):
        
        #for Jerry, get supervisors will return just him
        bosses = get_supervisors(self.employee1)
        shouldbe = [self.employee1]
        bosses = [unicode(x) for x in bosses]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        #for George get_supervisor will return he and Jerry
        bosses = get_supervisors(self.employee2)
        shouldbe = [self.employee2, self.employee1]
        bosses = [unicode(x) for x in bosses]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        #for Kramer get_supervisor will return he and Jerry        
        bosses = get_supervisors(self.employee3)
        shouldbe = [self.employee3, self.employee1]
        bosses = [unicode(x) for x in bosses]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        #for Elaine get_supervisor will return her, Kramer and Jerry
        bosses = get_supervisors(self.employee4)
        shouldbe = [self.employee4, self.employee3, self.employee1]
        bosses = [unicode(x) for x in bosses]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(bosses, shouldbe)

        #for Banya get_supervisor will return he, Kramer and Jerry
        bosses = get_supervisors(self.employee5)
        shouldbe = [self.employee5, self.employee3, self.employee1]
        bosses = [unicode(x) for x in bosses]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertEquals(bosses, shouldbe)

        #for Newman get_supervisor will return he, Banya, Kramer and Jerry
        bosses = get_supervisors(self.employee6)
        shouldbe = [self.employee6, self.employee5, self.employee3, 
                    self.employee1]
        bosses = [unicode(x) for x in bosses]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertEquals(bosses, shouldbe)

    def test_get_minions(self):
        
        # George, Elaine and Newman don't have anyone working for
        # them, so get_minions shouldn't return anyone but them for
        # George, get_minions will return just him
        minions = get_minions(self.employee2)
        shouldbe = [self.employee2]
        minions = [unicode(x) for x in minions]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(minions, shouldbe)

        # Banya is Newman's boss.  get_minions for Banya should return
        # both Banya and Newman
        minions = get_minions(self.employee5)
        shouldbe = [self.employee5, self.employee6]
        minions = [unicode(x) for x in minions]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(minions, shouldbe)

        # Kramer supervises Elaine and Banya directly, Banya
        # supervises Newman get_minions(Kramer) should return all four
        # employees.
        minions = get_minions(self.employee3)
        shouldbe = [self.employee3, self.employee4, self.employee5, 
                    self.employee6]
        minions = [unicode(x) for x in minions]
        shouldbe = [unicode(x) for x in shouldbe]
        self.assertListEqual(minions, shouldbe)

        # Jerry supervises everyone either directly or indirectly
        # get_minions(Jerry) should return all employees.
        minions = get_minions(self.employee1)
        shouldbe = [self.employee1, self.employee2, self.employee3, 
                    self.employee4, self.employee5, self.employee6]
        minions = [unicode(x) for x in minions]
        shouldbe = [unicode(x) for x in shouldbe]
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
    '''This suite of tests are to verify that the project method
    'milestone_complete' works as expected.  If a milestone has not
    been assigned to a project it should return None, if a milestone
    has been assigned but is still incomplete it should return False,
    and finally if it has been assigned and is complete, it should return true.

    There is also a test that verifies that milestones that have been
    revoked are returned as incomplete (False).

    '''

    def setUp(self):
        '''we will need one project with easy to rember project codes'''

        self.user = UserFactory(username = 'hsimpson',
                                first_name = 'Homer',
                                last_name = 'Simpson')
        
        self.milestone1 = MilestoneFactory.create(label="Approved",
                                             category = 'Core', order=1, 
                                             report=False)
        
        self.milestone2 = MilestoneFactory.create(label="Completed",
                                        category = 'Core', order=2, 
                                             report=False)
        
        self.project1 = ProjectFactory.create(prj_cd="LHA_IA12_111", 
                                              owner=self.user)

    def test_somthing_other_than_milestones(self):
        '''if we try to pass in something other than a milestone, we should
        handle it gracefully - return None'''

        #we pass in a non-sensical value, return None
        self.assertEquals(self.project1.milestone_complete('foobar'), None)

    def test_incomplete_milestones(self):
        '''If the milestone has been applied to the project but is still
        incomplete, return False.  This test takes advantage of the
        fact that all core requirements are automatically added when
        project is created.

        '''
        #this milestone hasn't been completed, our function should return false
        self.assertFalse(self.project1.milestone_complete(self.milestone2))

    def test_complete_milestones(self):
        '''If the milestone has been applied to the project and has been
        completed, return True'''

        #verify that our function returns False before we start
        self.assertFalse(self.project1.milestone_complete(self.milestone1))
        #use the project approve method to satisfy that milestone
        self.project1.approve()
        #verify that our function returns True now
        self.assertTrue(self.project1.milestone_complete(self.milestone1))

    def test_unassigned_milestones(self):
        '''an assigned milestone should return None'''

        #this is a new milestone, it won't be associated with this
        #project.  If we pass it into our method, we should get back
        #None.
        new_milestone = MilestoneFactory.create(label="UnAssigned Milestone",
                                        category = 'Core', order=999, 
                                             report=False)

        self.assertEqual(self.project1.milestone_complete(new_milestone), 
                         None)

    def test_revoked_milestones(self):
        '''a milestone that was satisfied, but then revoked by manager should
        be incomplete again'''

        #verify that it's not complete first
        self.assertFalse(self.project1.milestone_complete(self.milestone1))
        self.project1.approve()
        #now it is
        self.assertTrue(self.project1.milestone_complete(self.milestone1))
        #oh-oh it's been revoked!
        self.project1.unapprove()
        #our function should now return false
        self.assertFalse(self.project1.milestone_complete(self.milestone1))

    def tearDown(self):

        self.project1.delete()
        self.milestone1.delete()
        self.milestone2.delete()
        self.user.delete()