"""=============================================================
~/pjtk2/urls/project_crud.py
 Created: 25 Apr 2020 17:39:33

 DESCRIPTION:

  These are the urls associated with creating, retrieving, updating,
  and deleteing projects, reports, and milestones.

 A. Cottrill
=============================================================

"""

from django.conf import settings
from django.urls import path, re_path

from pjtk2.views import (
    # project CRUD
    new_project,
    copy_project,
    edit_project,
    project_detail,
    report_milestones,
    delete_report,
    report_upload,
    associated_file_upload,
    delete_associated_file,
)

PRJ_CD_REGEX = settings.PRJ_CD_REGEX

urlpatterns = [
    # ==============================
    #  Project CRUD
    path("newproject/", new_project, name="NewProject"),
    re_path((r"^copyproject/" + PRJ_CD_REGEX), copy_project, name="CopyProject"),
    re_path((r"^editproject/" + PRJ_CD_REGEX), edit_project, name="EditProject"),
    re_path((r"^projectdetail/" + PRJ_CD_REGEX), project_detail, name="project_detail"),
    # ==============================
    # Reports and milestones
    re_path(r"^reports/" + PRJ_CD_REGEX, report_milestones, name="Reports"),
    re_path(
        (
            r"^delete_report/"
            r"(?P<slug>[A-Za-z]{3}_[A-Za-z]{2}\d{2}_([A-Za-z]|\d){3})/"
            r"(?P<pk>\d+)/$"
        ),
        view=delete_report,
        name="delete_report",
    ),
    re_path((r"^reportupload/" + PRJ_CD_REGEX), report_upload, name="ReportUpload"),
    re_path(
        (r"^associatedfileupload/" + PRJ_CD_REGEX),
        associated_file_upload,
        name="associated_file_upload",
    ),
    path(
        "delete_associated_file/<int:id>/",
        view=delete_associated_file,
        name="delete_associated_file",
    ),
]
