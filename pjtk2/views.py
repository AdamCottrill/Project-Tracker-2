
# E1101 - Class 'whatever' has no 'something' member
# E1120 - No value passed for parameter 'cls' in function call
#pylint: disable=E1101, E1120

from django.views.generic import ListView
from django.views.generic.base import TemplateView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.core.servers.basehttp import FileWrapper
from django.forms.models import modelformset_factory
from django.forms.formsets import formset_factory
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.decorators import method_decorator

from pjtk2.functions import get_minions, my_messages, get_messages_dict

from pjtk2.filters import ProjectFilter
from pjtk2.models import (Milestone, Project, Report, ProjectMilestones,
                          Bookmark, Employee)#, my_messages)

from pjtk2.forms import (ProjectForm, ApproveProjectsForm, DocumentForm,
                         ReportsForm, SisterProjectsForm,  ReportUploadForm,
                         ReportUploadFormSet, NoticesForm)



import datetime
import pytz
import mimetypes
import os


def group_required(*group_names):
    """Requires user membership in at least one of the groups passed in."""
    #from:http://djangosnippets.org/snippets/1703/
    def in_groups(user):
        '''returns true if user is in one of the groups in group_names or is a
        superuser'''
        if user.is_authenticated():
            if (bool(user.groups.filter(name__in=group_names))
                    | user.is_superuser):
                return True
        return False
    return user_passes_test(in_groups)


def is_manager(user):
    '''A simple little function to find out if the current user is a
    manager (or better)'''
    if user.groups.filter(name='manager').count() > 0 | user.is_superuser:
        manager = True
    else:
        manager = False
    return(manager)


def can_edit(user, project):
    '''Another helper function to see if this user should be allowed
    to edit this project.  In order to edit the use must be either the
    project owner, a manager or a superuser.'''
    canedit = ((user.groups.filter(name='manager').count() > 0) or
               (user.is_superuser) or
               (user.username == project.owner.username))
    if canedit:
        canedit = True
    else:
        canedit = False
    return(canedit)


def get_assignments_with_paths(slug, core=True):
    '''function that will return a list of dictionaries for each of the
    reporting requirements.  each dictionary will indicate what the
    report is, whether or not it has been requested for this
    project, and if it is available, a path to the associated
    report.'''

    project = Project.objects.get(slug=slug)

    if core:
        assignments = project.get_core_assignments()
    else:
        assignments = project.get_custom_assignments()

    assign_dicts = []
    for assignment in assignments:
        try:
            filepath = Report.objects.get(projectreport=assignment,
                                          current=True)
        except Report.DoesNotExist:
            filepath = None
        required = assignment.required
        milestone = assignment.milestone
        category = assignment.milestone.category
        assign_dicts.append(dict(
            required=required,
            category=category,
            milestone=milestone,
            filepath=filepath
        ))
    return assign_dicts

#===========================
#Generic Views

class HomePageView(TemplateView):
    '''The page that will render first.'''
    template_name = "index.html"


class ListFilteredMixin(object):
    """ Mixin that adds support for django-filter
    from: https://github.com/rasca/django-enhanced-cbv/blob/master/
                          enhanced_cbv/views/list.py
    """

    filter_set = None

    def get_filter_set(self):
        if self.filter_set:
            return self.filter_set
        else:
            raise ImproperlyConfigured(
                "ListFilterMixin requires either a definition of "
                "'filter_set' or an implementation of 'get_filter()'")

    def get_filter_set_kwargs(self):
        """ Returns the keyword arguments for instanciating the filterset."""
        return {
            'data': self.request.GET,
            'queryset': self.get_base_queryset(),
        }

    def get_base_queryset(self):
        """ We can decided to either alter the queryset before or
        after applying the FilterSet """

        #==========
        self.tag = self.kwargs.pop('tag', None)
        if self.tag:
            queryset = Project.objects.filter(tags__name__in=[self.tag])
        else:
            queryset = Project.objects.all()
        return queryset
        #==========
        #return super(ListFilteredMixin, self).get_queryset()

    def get_constructed_filter(self):
        # We need to store the instantiated FilterSet cause we use it in
        # get_queryset and in get_context_data
        if getattr(self, 'constructed_filter', None):
            return self.constructed_filter
        else:
            filter = self.get_filter_set()(**self.get_filter_set_kwargs())
            self.constructed_filter = filter
            return filter

    def get_queryset(self):
        return self.get_constructed_filter().qs

    def get_context_data(self, **kwargs):
        kwargs.update({'filter': self.get_constructed_filter()})
        return super(ListFilteredMixin, self).get_context_data(**kwargs)


class ProjectList(ListFilteredMixin, ListView):
    """ A list view that can be filtered by django-filter """
    # modified to accept tag argument
    queryset = Project.objects.all()
    filter_set = ProjectFilter
    template_name = "ProjectList.html"

    def get_context_data(self, **kwargs):
        '''get any additional context information that has been passed in with
        the request.'''
        context = super(ProjectList, self).get_context_data(**kwargs)
        context['tag'] = self.tag
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        '''Override the dispatch method'''
        return super(ProjectList, self).dispatch(*args, **kwargs)

project_list = ProjectList.as_view()

#subset of projects tagged with tag:
taggedprojects = ProjectList.as_view()


class ApprovedProjectsList(ListView):
    '''A CBV that will render a list of currently approved project'''

    #queryset = Project.objects.filter(Approved = True)
    queryset = Project.objects.approved()
    template_name = "ApprovedProjectList.html"


    def get_context_data(self, **kwargs):
        context = super(ApprovedProjectsList, self).get_context_data(**kwargs)
        context['manager'] = is_manager(self.request.user)
        return context

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ApprovedProjectsList, self).dispatch(*args, **kwargs)

approved_projects_list = ApprovedProjectsList.as_view()



def logout_view(request):
    '''log the user out and redirect to the login page.'''
    logout(request)
    return HttpResponseRedirect(reverse('login'))

#===========================
# My application Views

@login_required
def project_detail(request, slug):
    '''View project details.'''

    project = get_object_or_404(Project, slug=slug)

    milestones = project.get_milestones()
    core = get_assignments_with_paths(slug)
    custom = get_assignments_with_paths(slug, core=False)

    user = User.objects.get(username__exact=request.user)
    edit = can_edit(user, project)
    manager = is_manager(user)

    return render_to_response('projectdetail.html',
                              {'milestones': milestones,
                               'Core': core,
                               'Custom': custom,
                               'project': project,
                               'edit': edit,
                               'manager': manager
                               },
                              context_instance=RequestContext(request))


def update_milestones(form_ms, milestones):
    '''a helper function to update milestones assocaited with a project.
    events that are in form_ms but have not been completed for this
    project will be updated with a time stamp, events associated with
    this project that are not in form_ms will have their time stamp
    cleared.

    milestones - queryset of milestones associated with a project
        generated by \n proj.get_milestones()

   forms_ms - list of projectmilestone id numbers generated from
        form.cleaned_data['milestones']

    '''
    #convert the list of milestones from the form to a set of integers:
    form_ms = set([int(x) for x in form_ms])

    old_completed = milestones.filter(completed__isnull=False)
    old_outstanding = milestones.filter(completed__isnull=True)

    old_completed = set([x.id for x in old_completed])
    old_outstanding = set([x.id for x in old_outstanding])

    now = datetime.datetime.now(pytz.utc)

    #these ones are now complete:
    added_ms = old_outstanding.intersection(form_ms)
    #ProjectMilestones.objects.filter(id__in=added_ms).update(completed=now)

    #in order to trigger a singal - we need to loop over each project
    #milestone, and mannually save them:
    for prjms_id in added_ms:
        prjms = ProjectMilestones.objects.get(id=prjms_id)
        prjms.completed = now
        prjms.save()

    #these ones were done, but now they aren't
    removed_ms = old_completed.difference(form_ms)
    #ProjectMilestones.objects.filter(id__in=removed_ms).update(completed=None)
    for prjms_id in removed_ms:
        prjms = ProjectMilestones.objects.get(id=prjms_id)
        prjms.completed = None
        prjms.save()


def edit_project(request, slug):
    '''if we are editing an existing project, first make sure that this
    user has priviledges to edit this project and if so, call
    crud_project with the slug of the project and with action set to
    Edit.  If not, redirectt them back to the details page for this
    slug.
    '''

    project = get_object_or_404(Project, slug=slug)

    if can_edit(request.user, project) is False:
        return HttpResponseRedirect(project.get_absolute_url())

    return crud_project(request, slug, action='Edit')


def copy_project(request, slug):
    '''if we are copying an existing project call crud_project with the
    slug of the original project and with action set to Copy'''
    return crud_project(request, slug, action='Copy')


def new_project(request):
    '''if this is a new project, call crud_project without a slug and
    with action set to New'''
    return crud_project(request, slug=None, action='New')


@login_required
def crud_project(request, slug, action='New'):
    '''A view to create, copy and edit projects, depending on the
    value of 'action'.'''

    if slug:
        instance = Project.objects.get(slug=slug)
        milestones = instance.get_milestones()
    else:
        instance = Project()
        milestones = None

    #find out if the user is a manager or superuser, if so set manager
    #to true so that he or she can edit all fields.
    user = User.objects.get(username__exact=request.user)
    manager = is_manager(user)

    if action == 'Copy':
        milestones = None

    if action == 'Edit':
        readonly = True
    else:
        readonly = False

    if request.method == 'POST':
        if action == 'Copy':
            instance = None
        form = ProjectForm(request.POST, instance=instance,
                           milestones=milestones,
                           readonly=readonly, manager=manager)
        if form.is_valid():
            tags = form.cleaned_data['tags']
            form_ms = form.cleaned_data.get('milestones', None)
            form = form.save(commit=False)
            if action == 'Copy' or action == 'New':
                form.owner = request.user
            form.save()
            form.tags.set(*tags)
            if form_ms:
                update_milestones(form_ms=form_ms, milestones=milestones)
            proj = Project.objects.get(slug=form.slug)
            return HttpResponseRedirect(proj.get_absolute_url())
        else:
            return render_to_response('ProjectForm.html',
                                      {'form': form,
                                       'action': action, 'project': instance},
                                      context_instance=RequestContext(request))
    else:
        form = ProjectForm(instance=instance, readonly=readonly,
                           manager=manager, milestones=milestones)

    return render_to_response('ProjectForm.html',
                              {'form': form,
                               'milestones': milestones,
                               'action': action, 'project': instance},
                              context_instance=RequestContext(request))


@login_required
#@permission_required('Project.can_change_Approved')
def approveprojects(request):
    '''create a list of projects, project names and an
    approved/unapproved checkbox widget.'''

    if is_manager(request.user) is False:
        return HttpResponseRedirect(reverse('ApprovedProjectsList'))

    project_formset = modelformset_factory(model=Project,
                                           form=ApproveProjectsForm,
                                           extra=0)

    #TODO - test that signed off and unactive projects are not included.
    #TODO - test that projects in the future are included in this year
    #thisyears = Project.this_year.all().filter(SignOff=False)
    #lastyears = Project.last_year.all().filter(SignOff=False)
    thisyears = Project.this_year.all()
    lastyears = Project.last_year.all()

    year = datetime.datetime.now().year

    if thisyears.count() == 0:
        this_year_empty = True
    else:
        this_year_empty = False

    if lastyears.count() == 0:
        last_year_empty = True
    else:
        last_year_empty = False

    if request.method == 'POST':
        if request.POST['form-type'] == u"thisyear":
            thisyearsformset = project_formset(request.POST,
                                               queryset=thisyears,
                                               prefix="thisyear")
            lastyearsformset = project_formset(queryset=lastyears,
                                               prefix="lastyear")

        elif request.POST['form-type'] == u"lastyear":
            lastyearsformset = project_formset(request.POST,
                                               queryset=lastyears,
                                               prefix="lastyear")
            thisyearsformset = project_formset(queryset=thisyears,
                                               prefix="thisyear")
        if thisyearsformset.is_valid():
            thisyearsformset.save()
            return HttpResponseRedirect(reverse('ApprovedProjectsList'))
        elif lastyearsformset.is_valid():
            lastyearsformset.save()
            return HttpResponseRedirect(reverse('ApprovedProjectsList'))
        else:
            return render_to_response('ApproveProjects.html',
                                      {
                                          'year': year,
                                          'thisYearEmpty': this_year_empty,
                                          'lastYearEmpty': last_year_empty,
                                          'thisyearsformset': thisyearsformset,
                                          'lastyearsformset':
                                          lastyearsformset},
                                      context_instance=RequestContext(request))
    else:
        thisyearsformset = project_formset(queryset=thisyears,
                                           prefix="thisyear")
        lastyearsformset = project_formset(queryset=lastyears,
                                           prefix="lastyear")

    return render_to_response('ApproveProjects.html',
                              {
                                  'year': year,
                                  'thisYearEmpty': this_year_empty,
                                  'lastYearEmpty': last_year_empty,
                                  'thisyearsformset': thisyearsformset,
                                  'lastyearsformset': lastyearsformset},
                              context_instance=RequestContext(request))


@login_required
@group_required('manager')
def report_milestones(request, slug):
    '''This function will render a form of requested reporting
    requirements for each project.  Used by managers to update
    reporting requirements for each project..'''

    project = Project.objects.get(slug=slug)
    reports = project.get_milestone_dicts()

    if request.method == "POST":
        new_report = request.POST.get('new_report', None)
        new_milestone = request.POST.get('new_milestone', None)
        if new_report or new_milestone:
            if new_report:
                new_report = new_report.title()
                #verify that this reporting requirement doesn't already exist
                # then add it to the reporting requirements
                try:
                    Milestone.objects.get_or_create(label=new_report,
                                                    report=True)
                except Milestone.DoesNotExist:
                    pass
            else:
                new_milestone = new_milestone.title()
                #verify that this reporting requirement doesn't already exist
                # then add it to the reporting requirements
                try:
                    Milestone.objects.get_or_create(label=new_milestone,
                                                    report=False)
                except Milestone.DoesNotExist:
                    pass

            #now redirect back to the update reports form for this project
            return HttpResponseRedirect(reverse('Reports',
                                                args=(project.slug,)))

        else:
            milestones = ReportsForm(request.POST, project=project,
                                      reports=reports, what='Milestones')
            core = ReportsForm(request.POST, project=project, reports=reports)
            custom = ReportsForm(request.POST, project=project,
                                 reports=reports, what='Custom')

            if core.is_valid() and custom.is_valid() and milestones.is_valid():
                core.save()
                custom.save()
                milestones.save()

                return HttpResponseRedirect(project.get_absolute_url())
    else:
        milestones = ReportsForm(project=project, reports=reports,
                                 what='Milestones')
        core = ReportsForm(project=project, reports=reports)
        custom = ReportsForm(project=project, reports=reports, what='Custom')

    return render_to_response('reportform.html',
                              {'Milestones': milestones,
                               'Core': core,
                               'Custom': custom,
                               'project': project
                               },
                              context_instance=RequestContext(request))


@login_required
def report_upload(request, slug):
    '''This view will render a formset with filefields for each of the
    reports associated with this project.  It used a custom formset
    that has been extended to accept a user and a project - these are
    needed to insert Reports.'''

    project = Project.objects.get(slug=slug)

    #get the core and custom reports associated with this project
    reports = get_assignments_with_paths(slug)
    custom = get_assignments_with_paths(slug, core=False)
    if custom:
        for report in custom:
            reports.append(report)

    report_formset = formset_factory(ReportUploadForm,
                                     formset=ReportUploadFormSet, extra=0)

    if request.method == 'POST':
        formset = report_formset(request.POST,  request.FILES,
                                 initial=reports,
                                 project=project,
                                 user=request.user)
        if formset.is_valid():
            for form in formset:
                form.save()
            return HttpResponseRedirect(project.get_absolute_url())
    else:
        formset = report_formset(initial=reports)
    return render_to_response('UploadReports.html',
                              {'formset': formset,
                               'project': project},
                              context_instance=RequestContext(request))


def serve_file(request, filename):
    '''from:http://stackoverflow.com/questions/2464888/
    downloading-a-csv-file-in-django?rq=1

    This function is my first attempt at a function used to
    serve/download files.  It works for basic text files, but seems to
    corrupt pdf and ppt files (maybe other binaries too).  It also
    should be updated to include some error trapping just incase the
    file doesn t actully exist.
    '''

    content_type = mimetypes.guess_type(filename)[0]

    #data = open(os.path.join(settings.MEDIA_ROOT,filename),'r').read()
    #resp = HttpResponse(data, mimetype='application/x-download')
    #resp = HttpResponse(data, mimetype=content_type)

    data = FileWrapper(file(os.path.join(settings.MEDIA_ROOT, filename), 'rb'))
    response = HttpResponse(data, mimetype=content_type)
    filename = os.path.split(filename)[-1]
    response['Content-Disposition'] = 'attachment;filename=%s' % filename

    return response


@login_required
def my_projects(request):
    '''gather all of the things a user needs and render them on a single
    page.'''
    #TODO - write more tests to verify this works as expected.
    bookmarks = Bookmark.objects.filter(user__pk=request.user.id)

    user = User.objects.get(username__exact=request.user)

    #make sure that the user exists - otherwise redirect them to a
    #help page
    try:
        myself = Employee.objects.get(user=user)
    except:
        msg = '''Your employee profile does not appear to be propery
                 configured.\nPlease contact the site administrators.'''
        messages.error(request, msg)
        raise Http404("Error")

    employees = get_minions(myself)
    employees = [x.user.username for x in employees]

    boss = False
    if len(employees) > 1:
        boss = True

    #I don't like how this takes three queries:
    submitted = Project.objects.submitted().filter(
        owner__username__in=employees)
    approved = Project.objects.approved().filter(
        owner__username__in=employees)
    complete = Project.objects.completed().filter(
        owner__username__in=employees)

    notices = get_messages_dict(my_messages(user))
    formset = formset_factory(NoticesForm, extra=0)

    if request.method == 'POST':
        notices_formset = formset(request.POST, initial=notices)
        if notices_formset.is_valid():
            for form in notices_formset:
                form.save()
            redirect_url = reverse('MyProjects') + '#tabs-2'
            return HttpResponseRedirect(redirect_url)
    else:
        notices_formset = formset(initial=notices)

    template_name = "my_projects.html"

    return render_to_response(template_name,
                              {'bookmarks': bookmarks,
                               'formset': notices_formset,
                               'complete': complete,
                               'approved': approved,
                               'submitted': submitted,
                               'boss': boss},
                              context_instance=RequestContext(request))


#=====================
#Bookmark views
@login_required
def bookmark_project(request, slug):
    '''Modified from Practical Django Projects - pg 189.  Add an entry in
    the bookmarks table for the given user and proejct.'''
    project = get_object_or_404(Project, slug=slug)
    try:
        Bookmark.objects.get(user__pk=request.user.id,
                             project__slug=project.slug)
    except Bookmark.DoesNotExist:
        Bookmark.objects.create(user=request.user,
                                           project=project)
    return HttpResponseRedirect(project.get_absolute_url())


@login_required
def unbookmark_project(request, slug):
    '''A function to remove a bookmark for a particular user and project'''
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST':
        Bookmark.objects.filter(user__pk=request.user.id,
                                project__pk=project.id).delete()
        return HttpResponseRedirect(project.get_absolute_url())
    else:
        return render_to_response('confirm_bookmark_delete.html',
                                  { 'project': project },
                                  context_instance=RequestContext(request))


def get_sisters_dict(slug):
    '''given a slug, return a list of dictionaries of projects that
    are (or could be) sisters to the given project.  Values returned
    by this function are used to populate the sister project formset'''

    project = get_object_or_404(Project, slug=slug)
    initial = []

    #family = project.get_family()
    sisters = project.get_sisters()
    candidates = project.get_sister_candidates()

    if sisters:
        for proj in sisters:
            initial.append(dict(sister=True,
                                prj_cd=proj.prj_cd,
                                slug=proj.slug,
                                prj_nm=proj.prj_nm,
                                prj_ldr=proj.prj_ldr,
                                url=proj.get_absolute_url()))
    if candidates:
        for proj in candidates:
            initial.append(dict(sister=False,
                                prj_cd=proj.prj_cd,
                                slug=proj.slug,
                                prj_nm=proj.prj_nm,
                                prj_ldr=proj.prj_ldr,
                                url=proj.get_absolute_url()))
    return initial


def sisterprojects(request, slug):
    '''render a form that can be used to create groupings of sister
    projects.  Only approved projects in the same year, and of the
    same project type will be presented.  existing sister projects
    will be checked off.  When the form is submitted the sibling
    relationships will be updated according to the values in the
    sister of each returned form.'''

    project = get_object_or_404(Project, slug=slug)
    initial = get_sisters_dict(slug)
    empty = True if len(initial) == 0 else False

    sister_formset = formset_factory(SisterProjectsForm, extra=0)

    if request.method == 'POST':
        formset = sister_formset(request.POST, request.FILES, initial=initial)
        if formset.is_valid():
            #see if any checkboxes have changed
            cleandata = [x.cleaned_data['sister'] for x in formset]
            init = [x.initial['sister'] for x in formset]
            #if cleandata==init, there is nothing to do
            if cleandata != init:
                #if all cleandata==False then remove this project from this
                #family
                if all(x is False for x in cleandata):
                    project.disown()
                else:
                    for form in formset:
                        form.save(parentslug=slug)
            return HttpResponseRedirect(project.get_absolute_url())
    else:
        formset = sister_formset(initial=initial)
    return render_to_response('SisterProjects.html',
                              {
                                  'formset': formset,
                                  'project': project,
                                  'empty': empty
                              },
                              context_instance=RequestContext(request))


def uploadlist(request):
    '''An example view that illustrates how to handle uploading files.
    basic, but functional.'''
    # Handle file upload
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            # Redirect to the document list after POST
            return HttpResponseRedirect(reverse('pjtk2.views.uploadlist'))
    else:
        form = DocumentForm() # A empty, unbound form
    # Load documents for the list page
    reports = Report.objects.all()
    # Render list page with the documents and the form
    return render_to_response(
        'upload_example.html',
        {'reports': reports, 'form': form},
        context_instance=RequestContext(request)
    )
