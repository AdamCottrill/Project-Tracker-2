"""=============================================================
 ~/pjtk2/views/project_crud.py
 Created: 24 Apr 2020 17:53:49

 DESCRIPTION:

  The views in this project are associated with creating, retrieving,
  pdating, and deleting individual projects.

 A. Cottrill
=============================================================

"""


from functools import partial, wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404

User = get_user_model()

from ..models import Project, ProjectFunding, AssociatedFile, Report

from ..forms import (
    ProjectForm,
    ProjectFundingForm,
    AssociatedFileUploadForm,
    ReportUploadForm,
    SpatialPointUploadForm,
)

from ..utils.helpers import (
    get_assignments_with_paths,
    is_dba,
    is_manager,
    can_edit,
    get_or_none,
    update_milestones,
)


# @login_required
def project_detail(request, slug):
    """
    View project details.
    """

    project = get_object_or_404(Project, slug=slug)

    milestones = project.get_milestones()
    core = get_assignments_with_paths(project)
    custom = get_assignments_with_paths(project, core=False)

    # user = User.objects.get(pk=request.user.id)
    user = get_or_none(User, pk=request.user.id)
    edit = can_edit(user, project)
    manager = is_manager(user)

    if project.cancelled:
        edit = False

    has_sister = project.has_sister()

    return render(
        request,
        "pjtk2/projectdetail.html",
        {
            "milestones": milestones,
            "Core": core,
            "Custom": custom,
            "project": project,
            "edit": edit,
            "manager": manager,
            "has_sister": has_sister,
        },
    )


def edit_project(request, slug):
    """
    if we are editing an existing project, first make sure that this
    user has priviledges to edit this project and if so, call
    crud_project with the slug of the project and with action set to
    Edit.  If not, redirectt them back to the details page for this
    slug.
    """

    project = get_object_or_404(Project, slug=slug)

    if can_edit(request.user, project) is False:
        return HttpResponseRedirect(project.get_absolute_url())

    return crud_project(request, slug, action="Edit")


def copy_project(request, slug):
    """
    if we are copying an existing project call crud_project with the
    slug of the original project and with action set to Copy
    """
    return crud_project(request, slug, action="Copy")


def new_project(request):
    """
    if this is a new project, call crud_project without a slug and
    with action set to New
    """

    return crud_project(request, slug=None, action="New")


@login_required
def crud_project(request, slug, action="New"):
    """
    A view to create, copy and edit projects, depending on the
    value of 'action'.
    """

    if slug:
        instance = Project.objects.get(slug=slug)
        orig_owner = instance.owner
        milestones = instance.get_milestones()
    else:
        instance = Project()
        milestones = None

    # find out if the user is a manager or superuser, if so set manager
    # to true so that he or she can edit all fields.
    user = User.objects.get(pk=request.user.id)
    manager = is_manager(user)
    dba = is_dba(user)

    if action == "Copy":
        milestones = None
        if not (dba or manager):
            instance.owner = user
            instance.prj_ldr = user
    if action == "Edit":
        readonly = True
    else:
        readonly = False

    if action == "New" and not (dba or manager):
        instance.owner = user

    ProjectFundingFormset = inlineformset_factory(
        Project, ProjectFunding, form=ProjectFundingForm, extra=2
    )

    if request.method == "POST":
        if action == "Copy":
            instance = None

        form = ProjectForm(
            request.POST,
            instance=instance,
            milestones=milestones,
            user=request.user,
            readonly=readonly,
            manager=manager,
            dba=dba,
        )

        funding_formset = ProjectFundingFormset(
            request.POST, request.FILES, instance=instance
        )

        # if form.owner is None and (dba or manager):
        #    form.owner = orig_owner

        if form.is_valid():
            tags = form.cleaned_data["tags"]
            form_ms = form.cleaned_data.get("milestones", None)
            form = form.save(commit=False)

            funding_formset = ProjectFundingFormset(request.POST, instance=form)
            if funding_formset.is_valid():
                form.save()
                funding_formset.save()
                form.tags.set(tags=tags)
                if form_ms:
                    update_milestones(form_ms=form_ms, milestones=milestones)
                proj = Project.objects.get(slug=form.slug)
                return HttpResponseRedirect(proj.get_absolute_url())
        else:
            return render(
                request,
                "pjtk2/ProjectForm.html",
                {
                    "form": form,
                    "funding_formset": funding_formset,
                    "action": action,
                    "project": instance,
                    "manager": manager,
                    "dba": dba,
                },
            )
    else:

        form = ProjectForm(
            instance=instance,
            readonly=readonly,
            user=request.user,
            manager=manager,
            dba=dba,
            milestones=milestones,
        )

    return render(
        request,
        "pjtk2/ProjectForm.html",
        {
            "form": form,
            "funding_formset": ProjectFundingFormset(instance=instance),
            "milestones": milestones,
            "action": action,
            "project": instance,
            "manager": manager,
            "dba": dba,
        },
    )


@login_required
def report_upload(request, slug):
    """
    This view will render a formset with filefields for each of the
    reports associated with this project.  It used a custom formset
    that has been extended to accept a user and a project - these are
    needed to insert Reports.
    """

    project = Project.objects.get(slug=slug)
    has_sister = project.has_sister()

    # get the core and custom reports associated with this project
    reports = get_assignments_with_paths(project)
    custom = get_assignments_with_paths(project, core=False)
    if custom:
        for report in custom:
            reports.append(report)

    report_formset = formset_factory(
        wraps(ReportUploadForm)(
            partial(ReportUploadForm, project=project, user=request.user)
        ),
        extra=0,
    )

    if request.method == "POST":
        formset = report_formset(request.POST, request.FILES, initial=reports)
        if formset.is_valid():
            for form in formset:
                form.save()
            return HttpResponseRedirect(project.get_absolute_url())
    else:
        formset = report_formset(initial=reports)

    return render(
        request,
        "pjtk2/UploadReports.html",
        {"formset": formset, "project": project, "has_sister": has_sister},
    )


@login_required
def delete_report(request, slug, pk):
    """
    This view removes a report from the project detail page.  For the
    user, it will appear as though the report has been deleted.  In
    reality, the report is simply updated so that it is not longer
    rendered and available on the project detail page but it will
    still exist on the file system.

    If this is a get request, redirect to a confirmation page.  If it
    is a post, update the projectmilestone and redirect back to the
    project detail page.

    Arguments:
    - `request`:
    - `slug`:
    - `pk`:

    """
    report = get_object_or_404(Report, id=pk)
    project = get_object_or_404(Project, slug=slug)

    if not can_edit(request.user, project):
        return HttpResponseRedirect(project.get_absolute_url())

    if request.method == "POST":
        report.delete()
        return HttpResponseRedirect(project.get_absolute_url())
    else:
        return render(
            request,
            "pjtk2/confirm_report_delete.html",
            {"report": report, "project": project},
        )


@login_required
def associated_file_upload(request, slug):
    """
    This view will render a formset with filefields that can be used to
    upload files that will be associated with a specific project.
    """

    project = Project.objects.get(slug=slug)

    if request.method == "POST":
        form = AssociatedFileUploadForm(
            request.POST, request.FILES, project=project, user=request.user
        )
        if form.is_valid():
            form.save()
            # m = ExampleModel.objects.get(pk=course_id)
            # m.model_pic = form.cleaned_data['image']
            # m.save()
            return HttpResponseRedirect(project.get_absolute_url())

    else:
        return render(request, "pjtk2/UploadAssociatedFiles.html", {"project": project})


@login_required
def delete_associated_file(request, id):
    """
    This view deletes an associated file

    If this is a get request, redirect to a confirmation page.  If it
    is a post, delete the associated file o
    project detail page.

    Arguments:
    - `request`:
    - `slug`:
    - `pk`:

    """
    associated_file = get_object_or_404(AssociatedFile, id=id)
    project = associated_file.project

    if not can_edit(request.user, project):
        return HttpResponseRedirect(project.get_absolute_url())

    if request.method == "POST":
        associated_file.delete()
        return HttpResponseRedirect(project.get_absolute_url())
    else:
        return render(
            request,
            "pjtk2/confirm_file_delete.html",
            {"associated_file": associated_file, "project": project},
        )


@login_required
def spatial_point_upload(request, slug):
    """This view will allow authorized users to upload a xlsx or csv file
    containing spatial information for a specific project.

    """

    project = Project.objects.get(slug=slug)
    # verify that only authorized users can add spatial data.
    if can_edit(request.user, project) is False:
        return HttpResponseRedirect(project.get_absolute_url())

    if request.method == "POST":
        form = SpatialPointUploadForm(request.POST, request.FILES, project=project)
    else:
        form = SpatialPointUploadForm(project=project)

    if form.is_valid():
        form.save()
        return HttpResponseRedirect(project.get_absolute_url())

    else:
        return render(
            request,
            "pjtk2/UploadSpatialPoints.html",
            {"project": project, "form": form},
        )
