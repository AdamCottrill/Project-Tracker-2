from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, include, url


from haystack.forms import FacetedSearchForm
from haystack.query import SearchQuerySet
from haystack.views import FacetedSearchView

sqs = (SearchQuerySet().order_by('-year').facet('project_type').
       facet('lake').facet('funding'))


urlpatterns = patterns('pjtk2.views',

                       url(r'^search/$', FacetedSearchView(
                           form_class=FacetedSearchForm,
                           searchqueryset=sqs),
                           name='haystack_search'),


                       url(r'^about/$', 'about_view', name = 'about_view'),
                       url(r'^report_descriptions/$',
                           'report_desc_view',
                           name = 'report_desc_view'),

    #CRUD Projects
    url(r'^projects/$', 'project_list', name='ProjectList'),
    url(r'^projects/(?P<username>.+)/$',
        'user_project_list', name='user_project_list'),
    url(r'^projects/?q=$', 'project_list_q', name='ProjectList_q'),
    url(r'^projects/approved$', 'approved_projects_list',
        name='ApprovedProjectsList'),

    #project formset:
    url(r'^approveprojects/$', 'approveprojects', name='ApproveProjects'),
# url(r'^projectsbytype/(?P<projecttype>.+)$', 'projects_by_type',
#       name='ProjectsByType'),


    url((r'^approve_project/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'approve_project', name='approve_project'),
    #url((r'^unapprove_project/'
    #      '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
    #    'unapprove_project', name='unapprove_project'),
    url((r'^cancel_project/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'cancel_project', name='cancel_project'),

    url((r'^signoff_project/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'signoff_project', name='signoff_project'),



    url(r'^newproject/$', 'new_project', name='NewProject'),

    url((r'^copyproject/'
         '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'copy_project', name='CopyProject'),

    url((r'^editproject/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'edit_project', name='EditProject'),

    url((r'^projectdetail/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'project_detail', name='project_detail'),

    url(r'^myprojects/$', 'my_projects', name='MyProjects'),

    url(r'^employeeprojects/(?P<employee_name>.+)$', 'employee_projects',
        name='EmployeeProjects'),

    url((r'^sisterprojects/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'sisterprojects', name='SisterProjects'),

##     url(r'^projects/(?P<year>\d{4})/$',
##         'project_by_year', name='ProjectsByYear'),
##

    #tagging/keywords
    url(r'^taggedprojects/(?P<tag>.+)/$', 'taggedprojects',
        name='TaggedProjects'),

    url(r'^tags/$', 'project_tag_list',
        name='project_tag_list'),


    #projects by region of interest:
    url(r'^projects_roi/$', 'find_projects_roi_view', name='find_projects_roi'),

    #projects by management unit:
    #url(
    #    regex=r'^projects_managment_unit/(?P<mu>[-A-Za-z0-9]+)$',
    #    view=find_projects_mu_view,
    #    name='find_projects_mu'
    #    ),



# Reports and milestones
    url(r'^reports/(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$',
        'report_milestones', name='Reports'),

#    url(r'^reportformset/', 'report_formset', name='ReportFormSet'),

#    url((r'^updateassignments/'
#            '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
#        'update_assignments', name='UpdateAssignments'),


#url(r'^(?P<slug>[A-Z]{3}_[A-Z]{2}\d{2}_([A-Z]|\d){3})/$',
#       'project_milestones', name='ProjectMilestones'),


   url((r'^delete_report/'
        '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/'
        '(?P<pk>\d+)/$'),
        view='delete_report',
        name='delete_report'),


    url((r'^reportupload/'
        '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'report_upload', name='ReportUpload'),

    url((r'^associatedfileupload/'
        '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
        'associated_file_upload', name='associated_file_upload'),

   url((r'^delete_associated_file/'
        '(?P<id>\d+)/$'),
        view='delete_associated_file',
        name='delete_associated_file'),


    #url(r'^uploadlist/$', 'uploadlist', name='UploadList'),

    #this function is used to download reports and files from project pages
    url(r'^serve_file/(?P<filename>.+)/$', 'serve_file', name='serve_file'),

    url(r'^test_excel/$', 'excel_csv', name='excel_csv'),

#bookmarking
    url((r'^bookmarkproject/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
          'bookmark_project', name='Bookmark_Project'),

    url((r'^unbookmarkproject/'
          '(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/$'),
          'unbookmark_project', name='Unbookmark_Project'),

)
