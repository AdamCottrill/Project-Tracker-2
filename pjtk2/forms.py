# E1101 - Class 'whatever' has no 'something' member
# E1120 - No value passed for parameter 'cls' in function call
# pylint: disable=E1101, E1120

import csv
import datetime
import hashlib
import io
import re
from itertools import chain

import pytz
from django import forms
from django.contrib.auth import get_user_model

# from django.contrib.gis import forms
from django.contrib.gis.forms.fields import PolygonField
from django.contrib.gis.geos import Point
from django.core.validators import FileExtensionValidator
from django.db.models.aggregates import Max, Min
from django.forms import (
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    ValidationError,
)
from django.forms.formsets import BaseFormSet
from django.forms.widgets import (
    CheckboxInput,
    CheckboxSelectMultiple,
    mark_safe,
)

# from django.utils.encoding import force_unicode
from django.urls import reverse
from django.utils import timezone
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

# from olwidget.fields import MapField, EditableLayerField
from leaflet.forms.widgets import LeafletWidget
from openpyxl import load_workbook
from taggit.forms import TagField

from common.models import Lake

from .models import (
    AssociatedFile,
    Database,
    FundingSource,
    Messages2Users,
    Milestone,
    Project,
    ProjectFunding,
    ProjectImage,
    ProjectMilestones,
    ProjectProtocol,
    ProjectType,
    Report,
    SamplePoint,
)

User = get_user_model()

# ==================================
#  WIDGETS


def make_custom_datefield(fld, **kwargs):
    """from: http://strattonbrazil.blogspot.ca/2011/03/
    using-jquery-uis-date-picker-on-all.html"""
    from django.db import models

    formfield = fld.formfield(**kwargs)
    if isinstance(fld, models.DateField):
        formfield.widget.format = "%m/%d/%Y"
        formfield.widget.attrs.update({"class": "datepicker"})
    return formfield


class UserModelChoiceField(ModelChoiceField):
    """a custom model choice widget for user objects.  It will
    display user first and last name in list of available choices
    (rather than their official user name). modified from
    https://docs.djangoproject.com/en/dev/ref/forms/fields/#modelchoicefield.
    """

    def label_from_instance(self, obj):
        if obj.first_name:
            label = "{0} {1}".format(obj.first_name, obj.last_name)
        else:
            label = obj.__str__()
        return label


class UserMultipleChoiceField(ModelMultipleChoiceField):
    """a custom model choice widget for user objects.  It will
    display user first and last name in list of available choices
    (rather than their official user name). modified from
    https://docs.djangoproject.com/en/dev/ref/forms/fields/#modelchoicefield.
    """

    def label_from_instance(self, obj):
        if obj.first_name:
            label = "{0} {1}".format(obj.first_name, obj.last_name)
        else:
            label = obj.__str__()
        return label


class UserReadOnlyText(forms.TextInput):
    """a custom readonly text widget for user objects.  It will
    display user first and last name of user if available, otherwise
    username.
    """

    input_type = "text"

    def render(self, name, value, attrs=None, renderer=None):
        user = User.objects.get(id=value)
        if user.first_name:
            value = "{0} {1}".format(user.first_name, user.last_name)
        else:
            value = str(user)
        return value


class ReadOnlyText(forms.TextInput):
    """from:
    http://stackoverflow.com/questions/1134085/
                rendering-a-value-as-text-instead-of-field-inside-a-django-form
    modified to get milestone labels if name starts with 'projectmilestone'
    """

    input_type = "text"

    def render(self, name, value, attrs=None, renderer=None):
        if name.startswith("projectmilestone"):
            value = Milestone.objects.get(id=value).label
        elif value is None:
            value = ""
        return mark_safe(value)


class HyperlinkWidget(forms.Widget):
    """This is a widget that will insert a hyperlink to a project
    detail page in a form set."""

    def __init__(self, text, url="#", *args, **kwargs):
        self.url = url
        self.text = text
        super(HyperlinkWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        output = []
        output.append('<a href="%s">%s</a>' % (self.url, self.text))
        return mark_safe("".join(output))


class CheckboxSelectMultipleWithDisabled(CheckboxSelectMultiple):
    """Subclass of Django's checkbox select multiple widget that allows
    disabling checkbox-options.  To disable an option, pass a dict
    instead of a string for its label, of the form: {'label': 'option
    label', 'disabled': True}
    """

    # from http://djangosnippets.org/snippets/2786/
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        if value is None:
            value = []
        has_id = attrs and "id" in attrs
        final_attrs = self.build_attrs(attrs)

        output = [""]
        # Normalize to strings
        str_values = set([v for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            if "disabled" in final_attrs.keys():
                del final_attrs["disabled"]
            if isinstance(option_label, dict):
                if dict.get(option_label, "disabled"):
                    final_attrs = dict(final_attrs, disabled="disabled")
                option_label = option_label["label"]
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id="%s_%s" % (attrs["id"], i))
                label_for = ' for="%s"' % final_attrs["id"]
            else:
                label_for = ""
            chbox = CheckboxInput(
                final_attrs, check_test=lambda value: value in str_values
            )
            # option_value = force_unicode(option_value)
            rendered_cb = chbox.render(name, option_value)
            # option_label = conditional_escape(force_unicode(option_label))
            option_label = conditional_escape(option_label)
            output.append(
                '<div class="checkbox"><label%s>%s %s</label></div>'
                % (label_for, rendered_cb, option_label)
            )
        # output.append(u'</ul>')
        return mark_safe("\n".join(output))


# ==================================
#  FORMS


class NoticesForm(forms.Form):
    """This form is used to display un-read messages.  Once read, the user
    can click the read box and submit the form to remove them from the
    que."""

    read = forms.BooleanField(label="Read:", required=False)

    prj_nm = forms.CharField(widget=ReadOnlyText, label="Project Name", required=False)

    msg_id = forms.CharField(label="msg_id", required=False)

    user_id = forms.CharField(label="user_id", required=False)

    msg = forms.CharField(
        widget=ReadOnlyText, label="Message", max_length=80, required=False
    )

    def __init__(self, *args, **kwargs):
        super(NoticesForm, self).__init__(*args, **kwargs)

        self.fields["msg_id"].widget = forms.HiddenInput()
        self.fields["user_id"].widget = forms.HiddenInput()
        self.prj_cd = kwargs["initial"].get("prj_cd", None)
        self.url = kwargs["initial"].get("url", None)

        # use a hyperlink widget for the project code
        self.fields.update(
            {
                "prj_cd": forms.CharField(
                    widget=HyperlinkWidget(url=self.url, text=self.prj_cd),
                    label="Project Code",
                    max_length=13,
                    required=False,
                )
            }
        )

        # snippet makes sure that Approved appears first
        self.field_order = ["read", "prj_cd", "prj_nm", "msg", "msg_id", "user_id"]

    def save(self, *args, **kwargs):

        if self.cleaned_data["read"] is True:
            now = datetime.datetime.now(pytz.utc)
            msg_id = self.initial["msg_id"]
            user_id = self.initial["user_id"]

            message2user = Messages2Users.objects.filter(id=msg_id, user__id=user_id)
            message2user.update(read=now)


class ApproveProjectsForm(forms.ModelForm):
    """This project form is used for view to approve/unapprove
    multiple projects."""

    prj_nm = forms.CharField(widget=ReadOnlyText, label="Project Name", required=False)

    # prj_ldr = forms.CharField(
    #    label = "Project Leader",
    #    max_length = 80,
    #    required = False,
    # )

    class Meta:
        model = Project
        fields = ("prj_cd", "prj_nm", "prj_ldr", "project_type")

    def __init__(self, *args, **kwargs):
        super(ApproveProjectsForm, self).__init__(*args, **kwargs)

        self.fields["Approved"] = forms.BooleanField(
            label="Approved", required=False, initial=self.instance.is_approved()
        )

        self.fields["prj_ldr"].widget = forms.HiddenInput()

        self.fields["prj_ldr_label"] = forms.CharField(
            widget=ReadOnlyText,
            label="Project Leader",
            required=False,
            initial="{0} {1}".format(
                self.instance.prj_ldr.first_name, self.instance.prj_ldr.last_name
            ),
        )

        self.fields["project_type"].widget = forms.HiddenInput()

        self.fields["project_type_label"] = forms.CharField(
            widget=ReadOnlyText,
            label="Project Type",
            required=False,
            initial=self.instance.project_type,
        )

        self.fields.update(
            {
                "prj_cd": forms.CharField(
                    widget=HyperlinkWidget(
                        url=self.instance.get_absolute_url(), text=self.instance.prj_cd
                    ),
                    label="Project Code",
                    max_length=12,
                    required=False,
                )
            }
        )

        # snippet makes sure that Approved appears first
        self.field_order = [
            "Approved",
            "prj_cd",
            "prj_nm",
            "project_type_label",
            "prj_ldr_label",
        ]

    def clean_prj_cd(self):
        """return the original value of prj_cd"""
        return self.instance.prj_cd

    def clean_prj_nm(self):
        """return the original value of prj_nm"""
        return self.instance.prj_nm

    def clean_project_type(self):
        """return the original value of prj_nm"""
        return self.instance.project_type

    def clean_prj_ldr(self):
        """return the original value of prj_ldr"""
        return self.instance.prj_ldr

    def clean_prj_ldr_label(self):
        """return the original value of prj_ldr_label none - make sure
        nothing is returned
        """
        return None

    def save(self, commit=True):
        if self.has_changed:
            if self.cleaned_data["Approved"]:
                self.instance.approve()
            else:
                self.instance.unapprove()
        return super(ApproveProjectsForm, self).save(commit)


class ApproveProjectsForm2(forms.Form):
    """This project form is used for view to approve/unapprove
    multiple projects."""

    id = forms.CharField(widget=forms.HiddenInput())
    lake = forms.CharField(widget=forms.HiddenInput())
    approved = forms.BooleanField(required=False)
    # prj_cd = forms.CharField(widget=ReadOnlyText, label="Project Code", required=False)
    prj_nm = forms.CharField(widget=ReadOnlyText, label="Project Name", required=False)
    prj_ldr_label = forms.CharField(
        widget=ReadOnlyText, label="Project Lead", required=False
    )
    project_type = forms.CharField(
        widget=ReadOnlyText, label="Project Type", required=False
    )
    protocol = forms.CharField(widget=ReadOnlyText, label="Protocol", required=False)

    def __init__(self, *args, **kwargs):

        super(ApproveProjectsForm2, self).__init__(*args, **kwargs)

        self.fields["approved"].widget.attrs["class"] = "form-check-input"

        self.initial = kwargs.get("initial", {})

        prj_cd = self.initial.get("prj_cd", None)
        if prj_cd:
            self.fields.update(
                {
                    "prj_cd": forms.CharField(
                        widget=HyperlinkWidget(
                            url=reverse("project_detail", kwargs={"slug": prj_cd}),
                            text=prj_cd,
                        ),
                        label="Project Code",
                        max_length=12,
                        required=False,
                    )
                }
            )

            # make sure that Approved appears first
            self.order_fields(
                [
                    "approved",
                    "prj_cd",
                    "prj_nm",
                    "prj_ldr_label",
                    "project_type",
                    "protocol",
                    "id",
                    "lake",
                ]
            )

    def clean_prj_cd(self):
        """return the original value of prj_cd"""
        return self.initial.get("prj_cd", "")

    def clean_prj_nm(self):
        """return the original value of prj_nm"""
        return self.initial.get("prj_nm", "")

    def clean_project_type(self):
        """return the original value of prj_type"""
        return self.initial.get("project_type", "")

    def clean_protocol(self):
        """return the original value of protocol"""
        return self.initial.get("protocol", "")

    def clean_prj_ldr_label(self):
        """return the original value of prj_ldr_label none - make sure
        nothing is returned
        """
        return self.initial.get("prj_ldr_label", "")

    def save(self, commit=True):

        # approved_now = self.cleaned_data["approved"]
        # approved_before = self.initial["approved"]

        # if approved_now is not approved_before:
        if self.has_changed():
            id = self.cleaned_data["id"]
            pms = ProjectMilestones.objects.get(id=id)
            if self.cleaned_data["approved"]:
                now = timezone.now()
            else:
                now = None
            pms.completed = now
            # need to call save to send signals:
            pms.save()

        return None


class ReportsForm(forms.Form):
    """This form is used to update reporting requirements for a
    particular project.  Checkbox widgets are dynamically added to the
    form depending on reports identified as core plus any additional
    custom reports requested by the manager."""

    def __init__(self, *args, **kwargs):
        self.milestones = kwargs.pop("reports")
        self.what = kwargs.pop("what", "Core")
        self.project = kwargs.pop("project", None)

        super(ReportsForm, self).__init__(*args, **kwargs)

        reports = self.milestones[self.what]["milestones"]
        assigned = self.milestones[self.what]["assigned"]

        self.fields[self.what] = forms.MultipleChoiceField(
            choices=reports,
            initial=assigned,
            label="",
            required=False,
            widget=forms.widgets.CheckboxSelectMultiple(),
        )

    def save(self):
        """in order for a milestone to be associated with a project, it must
        have a record in ProjectMilestones with required=True.  There
        are three logic paths we have to cover:\n
        - records in ProjectMilestones that need to have required set to True
        - records in ProjectMilestones that need to have required set to False
        - records tht need to be added to ProjectMilestones
        """

        cleaned_data = self.cleaned_data
        project = self.project
        what = self.what

        existing = project.get_milestone_dicts()[what]["assigned"]
        values = list(cleaned_data.values())[0]
        cleaned_list = [int(x) for x in values]

        # these are the milestones that are existing but not in cleaned_data
        turn_off = list(set(existing) - set(cleaned_list))
        # these are the milestones that were not assigned but they are
        # now in cleaned data.
        turn_on = list(set(cleaned_list) - set(existing))

        # turn OFF any ProjectMilestones that are not in cleaned data
        ProjectMilestones.objects.filter(
            project=project, milestone__id__in=turn_off
        ).update(required=False)

        # turn on any ProjectMilestones that are in cleaned data
        ProjectMilestones.objects.filter(
            project=project, milestone__id__in=turn_on
        ).update(required=True)

        # new records can be identified as milestone id's in cleaned
        # data that are not in ProjectMilestone
        projmst = ProjectMilestones.objects.filter(project=project).values(
            "milestone__id"
        )
        projmst = [x["milestone_id"] for x in projmst.values()]

        new = list(set(cleaned_list) - set(projmst))

        # now loop over new milestones adding a new record to ProjectReports for
        # each one with required=True
        if new:
            for milestone in new:
                ProjectMilestones.objects.create(
                    project=project, required=True, milestone_id=milestone
                )


# class ReportUploadFormSet(BaseFormSet):
#    '''modified from
#    here:http://stackoverflow.com/questions/
#                     5426031/django-formset-set-current-user
#    allows additional parameters to be passed to formset.  Project and
#    user are required to upload reports.
#
#    This formset is used to upload the reports for a particular
#    project.  It will generate one reportUploadForm for each reporting
#    requirement (all core reports plus any additional reports that
#    have been requested).
#
#    Additionally, the project and user id will associated with each
#    form so that they can be appended and uploaded properly.
#    '''
#    def __init__(self, *args, **kwargs):
#        self.project = kwargs.pop('project', None)
#        self.user = kwargs.pop('user', None)
#        super(ReportUploadFormSet, self).__init__(*args, **kwargs)
#        for form in self.forms:
#            form.empty_permitted = False
#
#    def _construct_forms(self):
#        if hasattr(self,"_forms"):
#            return self._forms
#        self._forms = []
#        for i in range(self.total_form_count()):
#            self._forms.append(self._construct_form(i,
#                                                   project=self.project,
#                                                   user=self.user))
#        return self._forms
#
#    forms = property(_construct_forms)


class ReportUploadForm(forms.Form):
    """This form is used in ReportUploadFormset to upload files. Each
    form includes a label for the report type, a read only checkbox
    indicating whether or not this report is required, and a file
    input widget."""

    required = forms.BooleanField(label="Required", required=False)

    milestone = forms.CharField(
        widget=ReadOnlyText, label="Report Name", required=False
    )

    report_path = forms.FileField(label="File", required=False)

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project")
        self.user = kwargs.pop("user")
        super(ReportUploadForm, self).__init__(*args, **kwargs)
        self.fields["required"].widget.attrs["disabled"] = True
        # self.fields["report_path"].widget.attrs['style'] = "text-align: right;"
        self.fields["report_path"].widget.attrs["size"] = "40"
        self.fields["report_path"].widget.attrs["class"] = "fileinput"

        if self.project.has_sister():
            initial = kwargs.get("initial")
            if initial:
                ms = initial.get("milestone")
                if ms.shared:
                    new_class = "fileinput shared"
                    self.fields["report_path"].widget.attrs["class"] = new_class

    def clean_milestone(self):
        """return the original value of milestone"""
        return self.initial["milestone"]

    def clean_required(self):
        """return the original value of required"""
        return self.initial["required"]

    def save(self):
        """see if a report already exists for this projectreport, if
        so, make sure that it Current flag is set to false

        - populate uploaded by with user name

        - TODO:calculate hash of file (currently calculated on hash of path)

        - TODO:verify that it matches certain criteria (file
        types/extentions) depending on reporting milestone

        - if this is a presentation or summary report, see if the
        project has any sister projects, if so, update projectreports
        for them too.
        """

        now = datetime.datetime.now(pytz.utc)

        if "report_path" in self.changed_data and self.cleaned_data["report_path"]:

            projectreport = ProjectMilestones.objects.get(
                project=self.project, milestone=self.clean_milestone()
            )

            # see if there is already is a report for this projectreport
            try:
                oldReport = Report.objects.get(
                    projectreport=projectreport, current=True
                )
            except Report.DoesNotExist:
                oldReport = None

            # if so set the 'current' attribure of the old report to
            # False so that it can be replaced by the new one (there
            # can only ever be one 'current' report)
            if oldReport:
                oldReport.current = False
                oldReport.save()

            self.is_valid()  # just to make sure

            report_path = self.cleaned_data["report_path"]
            report_hash = hashlib.sha1(str(report_path).encode("utf-8")).hexdigest()

            newReport = Report(
                report_path=report_path, uploaded_by=self.user, report_hash=report_hash
            )

            newReport.save()
            # add the m2m record for this projectreport
            newReport.projectreport.add(projectreport)

            projectreport.completed = now
            projectreport.save()

            # if this a presentation or summary report, see if
            # this project has any sister projects.  If so, add an m2m
            # for each one so this document is associated with them
            # too.
            # TODO: figure out how to handle sisters
            # that are adopted or dis-owned - how do we synchronize
            # existing files?

            sisters = self.project.get_sisters()

            shared_milestones = Milestone.objects.shared()
            shared_labels = [x.label for x in shared_milestones]

            # common = str(self.clean_milestone()) in ["Proposal Presentation",
            #                                    "Completetion Presentation",
            #                                    "Summary Report",]
            common = str(self.clean_milestone()) in shared_labels

            if sisters and common:
                for sister in sisters:
                    projreport, created = ProjectMilestones.objects.get_or_create(
                        project=sister, milestone=self.clean_milestone()
                    )
                    try:
                        oldReport = Report.objects.get(
                            projectreport=projreport, current=True
                        )
                        oldReport.current = False
                        oldReport.save()
                    except Report.DoesNotExist:
                        oldReport = None
                    # add the m2m relationship for the sister
                    newReport.projectreport.add(projreport)
                    projectreport.completed = now
                    projectreport.save()


class ProjectForm(forms.ModelForm):
    """This a form for new projects using crispy-forms and including
    cleaning methods to ensure that project code is valid, dates agree
    and ....  for a new project, we need project code, name, comment,
    leader, start date, end date, database, project type,"""

    prj_nm = forms.CharField(label="Project Name:", required=True)

    prj_cd = forms.CharField(label="Project Code:", max_length=12, required=True)

    prj_ldr = UserModelChoiceField(
        label="Project Leader:",
        queryset=User.objects.filter(is_active=True).order_by(
            "first_name", "last_name"
        ),
        required=True,
    )

    field_ldr = UserModelChoiceField(
        label="Field Leader:",
        queryset=User.objects.filter(is_active=True).order_by(
            "first_name", "last_name"
        ),
        required=False,
    )

    owner = UserModelChoiceField(
        label="Data Custodian/Project Owner:",
        queryset=User.objects.filter(is_active=True).order_by(
            "first_name", "last_name"
        ),
        required=True,
    )

    project_team = UserMultipleChoiceField(
        label="Other Team Members (optional)",
        widget=forms.SelectMultiple(attrs={"size": 15}),
        queryset=User.objects.filter(is_active=True).order_by(
            "first_name", "last_name"
        ),
        required=False,
    )

    abstract = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "input-xxlarge",
                "rows": 20,
                "cols": 60,
                "aria-label": "project-abstract",
            }
        ),
        label="Project Abstract (public):",
        required=True,
    )

    comment = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "input-xxlarge",
                "rows": 20,
                "cols": 60,
                "aria-label": "project-comments-remarks",
            }
        ),
        label="Comments, Concerns or Remarks:",
        required=False,
    )

    risk = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "input-xxlarge",
                "rows": 20,
                "cols": 60,
                "aria-label": "project-risks",
            }
        ),
        label="Risks associated with not running project:",
        required=False,
    )

    prj_date0 = forms.DateField(
        widget=forms.DateInput(attrs={"class": "datepicker"}),
        label="Start Date:",
        required=True,
        input_formats=["%d/%m/%Y", "%Y-%m-%d"],
    )

    prj_date1 = forms.DateField(
        widget=forms.DateInput(attrs={"class": "datepicker"}),
        label="End Date:",
        required=True,
        input_formats=["%d/%m/%Y", "%Y-%m-%d"],
    )

    project_type = forms.ModelChoiceField(
        label="Project Type:",
        queryset=ProjectType.objects.all().order_by("project_type"),
        required=True,
    )

    protocol = forms.ModelChoiceField(
        label="Protocol:",
        queryset=ProjectProtocol.objects.filter(deprecated__isnull=True).order_by(
            "protocol"
        ),
        required=False,
    )

    master_database = forms.ModelChoiceField(
        label="Master Database:", queryset=Database.objects.all(), required=True
    )

    lake = forms.ModelChoiceField(
        label="Lake:", queryset=Lake.objects.all(), required=True
    )

    dba = UserModelChoiceField(
        label="DBA:",
        # TODO - change this from superuser to groups__contain='dba'
        queryset=User.objects.filter(is_active=True)
        .filter(employee__role__in=["dba"])
        .order_by("first_name", "last_name"),
        required=True,
    )

    tags = TagField(
        label="Keywords:", required=False, help_text="<em>(comma separated values)</em>"
    )

    class Meta:
        model = Project
        fields = (
            "prj_nm",
            "prj_ldr",
            "field_ldr",
            "owner",
            "prj_cd",
            "prj_date0",
            "prj_date1",
            "risk",
            "project_type",
            "protocol",
            "master_database",
            "lake",
            "abstract",
            "comment",
            "dba",
            "tags",
            "project_team",
        )

    def __init__(self, *args, **kwargs):
        readonly = kwargs.pop("readonly", False)
        manager = kwargs.pop("manager", False)
        dba = kwargs.pop("dba", False)

        self.user = kwargs.pop("user", None)

        milestones = kwargs.pop("milestones", None)

        super(ProjectForm, self).__init__(*args, **kwargs)

        self.fields[
            "project_team"
        ].help_text = "Control-click to select more than one team member."

        for visible in self.visible_fields():
            if "class" in visible.field.widget.attrs.keys():
                class_attrs = visible.field.widget.attrs["class"]
            else:
                class_attrs = ""
            visible.field.widget.attrs["class"] = "form-control " + class_attrs

        self.readonly = readonly
        self.manager = manager
        self.dba = dba

        self.fields["tags"].widget.attrs["aria-label"] = "keywords"

        if not (manager or dba):
            self.fields["owner"].required = False
            self.fields["owner"].widget.attrs["disabled"] = "disabled"
            # self.fields["owner"].widget.attrs["readonly"] = True

        if readonly:
            self.fields["prj_cd"].widget.attrs["readonly"] = True
            # this is an edit so our project lead could be anyone:
            self.fields["prj_ldr"].queryset = User.objects.order_by(
                "first_name", "last_name"
            ).all()
            self.fields["field_ldr"].queryset = User.objects.order_by(
                "first_name", "last_name"
            ).all()

            self.fields["owner"].queryset = (
                User.objects.order_by("first_name", "last_name")
                .filter(is_active=True)
                .all()
            )

        if milestones:
            if self.manager is True:
                choices = [
                    (x.id, {"label": x.milestone.label, "disabled": False})
                    for x in milestones
                ]
            else:
                choices = [
                    (
                        x.id,
                        {"label": x.milestone.label, "disabled": x.milestone.protected},
                    )
                    for x in milestones
                ]

            # *** NOTE ***
            #'completed' must be a list of values that match the choices (above)
            completed = [x.id for x in milestones if x.completed is not None]
            self.fields.update(
                {
                    "milestones": forms.MultipleChoiceField(
                        widget=CheckboxSelectMultipleWithDisabled(),
                        choices=choices,
                        label="",
                        initial=completed,
                        required=False,
                    )
                }
            )

    def save(self, commit=True):
        """Override the save method to save many-2-many relationships."""
        # Get the unsaved project instance
        instance = forms.ModelForm.save(self, False)

        # Prepare a 'save_m2m' method for the form,
        old_save_m2m = self.save_m2m

        def save_m2m():
            old_save_m2m()
            instance.project_team.clear()
            project_team = self.cleaned_data.get("project_team")

            if project_team:
                for member in project_team:
                    instance.project_team.add(member)

        self.save_m2m = save_m2m

        instance.save()
        self.save_m2m()

        return instance

    def clean_owner(self):
        """if the user is not a manager or a dba, they must be the owner"""

        if not (self.manager or self.dba):
            return self.user
        else:
            return self.cleaned_data["owner"]

    def clean_approved(self):
        """if this wasn't a manager, reset the Approved value to the
        original (read only always returns false)"""
        if self.manager:
            return self.cleaned_data["Approved"]
        else:
            return self.instance.Approved

    def clean_prj_cd(self):
        """a clean method to ensure that the project code matches the
        given regular expression.  method also ensure that project
        code is unique.  If duplicate code is entered, an error
        message will be displayed including link to project with that
        project code.  The method only applies to new projects.  When
        editing a project, project code is readonly and does need to be checked.
        """
        pattern = r"^[A-Z]{3}_[A-Z]{2}\d{2}_([A-Z]|\d){3}$"
        project_code = self.cleaned_data["prj_cd"]

        if self.readonly == False:
            if re.search(pattern, project_code):
                # make sure that this project code doesn't already exist:
                try:
                    proj = Project.objects.get(prj_cd=project_code)
                except Project.DoesNotExist:
                    proj = None
                if proj:
                    url = proj.get_absolute_url()
                    errmsg = (
                        "Project Code already exists (<a href='%s'>view</a>)." % url
                    )
                    raise forms.ValidationError(mark_safe(errmsg))
                else:
                    return project_code
            else:
                raise forms.ValidationError("Malformed Project Code.")
        else:
            # do nothing, just return the project code as is
            return project_code

    def clean_tags(self):
        """
        Force all tags to lowercase.
        modified from:http://stackoverflow.com/questions/25676952/
        """
        tags = self.cleaned_data.get("tags", None)
        if tags:
            tags = list(set([t.lower() for t in tags]))

        return tags

    def clean(self):
        """make sure that project start and end dates are in the same
        year, and that the start date occurs before the end date.
        Also make sure that the year in project code matches the start
        and end dates."""

        cleaned_data = super(ProjectForm, self).clean()
        start_date = cleaned_data.get("prj_date0")
        end_date = cleaned_data.get("prj_date1")
        project_code = cleaned_data.get("prj_cd")

        # if this is not a manager, the protected fields will not be
        # included in the cleaned data for the milestones - we need to
        # add them back in
        form_ms = cleaned_data.get("milestones")
        if form_ms:
            if not self.manager:
                ms = self.instance.get_milestones()
                protected_ms = [
                    x.id
                    for x in ms
                    if x.milestone.protected and x.completed is not None
                ]
                cleaned_data["milestones"].extend(protected_ms)

        if start_date and end_date and project_code:

            if end_date < start_date:
                errmsg = "Project end date occurs before start date."
                raise forms.ValidationError(errmsg)

            if end_date.year != start_date.year:
                errmsg = "Project start and end date occur in different years."
                raise forms.ValidationError(errmsg)

            if end_date.strftime("%y") != project_code[6:8]:
                errmsg = "Project dates do not agree with project code."
                raise forms.ValidationError(errmsg)
        return cleaned_data


class ProjectFundingForm(forms.ModelForm):
    """Form for funding sources and amounts for each source of funding
    for each project

    """

    source = forms.ModelChoiceField(
        label="Funding Source:", queryset=FundingSource.objects.all(), required=True
    )

    salary = forms.DecimalField(required=False, decimal_places=2)
    odoe = forms.DecimalField(required=False, decimal_places=2)

    class Meta:
        model = ProjectFunding
        fields = ["source", "salary", "odoe"]
        exclude = ["project"]

    def __init__(self, *args, **kwargs):
        super(ProjectFundingForm, self).__init__(*args, **kwargs)

        for fld in self.visible_fields():
            if "class" in fld.field.widget.attrs.keys():
                class_attrs = fld.field.widget.attrs["class"]
            else:
                class_attrs = ""
            fld.field.widget.attrs["class"] = "form-control " + class_attrs


class SisterProjectsForm(forms.Form):
    """This project form is used to identify sister projects"""

    sister = forms.BooleanField(label="Sister:", required=False)

    prj_nm = forms.CharField(widget=ReadOnlyText, label="Project Name", required=False)

    slug = forms.CharField(label="slug", required=False)

    prj_ldr = forms.CharField(
        widget=ReadOnlyText, label="Project Leader", max_length=80, required=False
    )

    def __init__(self, *args, **kwargs):
        super(SisterProjectsForm, self).__init__(*args, **kwargs)

        self.fields["slug"].widget = forms.HiddenInput()
        self.prj_cd = kwargs["initial"].get("prj_cd", None)
        self.url = kwargs["initial"].get("url", None)

        # use a hyperlink widget for the project code
        self.fields.update(
            {
                "prj_cd": forms.CharField(
                    widget=HyperlinkWidget(url=self.url, text=self.prj_cd),
                    label="Project Code",
                    max_length=13,
                    required=False,
                )
            }
        )

        # snippet makes sure that Approved appears first
        self.field_order = ["sister", "prj_cd", "prj_nm", "prj_ldr", "slug"]

    def clean_prj_cd(self):
        """return the original value of prj_cd"""
        return self.initial["prj_cd"]

    def clean_prj_nm(self):
        """return the original value of prj_nm"""
        return self.initial["prj_nm"]

    def clean_prj_ldr(self):
        """return the original value of prj_ldr"""
        return self.initial["prj_ldr"]

    def save(self, *args, **kwargs):
        # family = kwargs.pop('family', None)
        parentslug = kwargs.pop("parentslug")
        parentProject = Project.objects.get(slug=parentslug)
        slug = self.cleaned_data["slug"]
        # 1. if sister was true and is now false, remove that
        # project from the family
        if self.cleaned_data["sister"] is False and self.initial["sister"] is True:
            parentProject.delete_sister(slug)
        # 2. if sister was false and is now true, add this project to the family.
        elif self.cleaned_data["sister"] is True and self.initial["sister"] is False:
            parentProject.add_sister(slug)
        # do nothing
        else:
            pass


class AssociatedFileUploadForm(forms.Form):
    """A simple little form for uploading files one at a time."""

    file_path = forms.FileField(label="File", required=False)

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project")
        self.user = kwargs.pop("user")
        super(AssociatedFileUploadForm, self).__init__(*args, **kwargs)
        self.fields["file_path"].widget.attrs["size"] = "40"
        self.fields["file_path"].widget.attrs["class"] = "fileinput"

    def save(self):
        """fill in the project, user, uploaded time and file hash when we save
        it."""

        fname = str(self.cleaned_data["file_path"])

        newReport = AssociatedFile(
            project=self.project,
            file_path=self.cleaned_data["file_path"],
            uploaded_by=self.user,
            hash=hashlib.sha1(fname.encode("utf-8")).hexdigest(),
        )
        newReport.save()


class GeoForm(forms.Form):
    """ """

    selection = PolygonField(widget=LeafletWidget(), required=True)

    project_types = forms.ModelMultipleChoiceField(
        (ProjectType.objects.filter(field_component=True).order_by("project_type")),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label="Project Type",
    )

    first_year = forms.IntegerField(required=False)
    last_year = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        """Pre-populate the first_year and last_year years with actual values in
        the database."""
        super(GeoForm, self).__init__(*args, **kwargs)

        qs = Project.objects.values("year").aggregate(
            last_year=Max("year"), first_year=Min("year")
        )

        self.first_year = qs["first_year"]
        self.last_year = qs["last_year"]

        self.fields["first_year"].widget.attrs["placeholder"] = self.first_year
        self.fields["last_year"].widget.attrs["placeholder"] = self.last_year

    def clean_first_year(self):
        """If we can't convert the first_year year value to an integer,
        throw an error"""
        yr = self.cleaned_data["first_year"]
        if yr:
            try:
                yr = int(yr)
            except ValueError:
                msg = "'First_Year Year' must be numeric."
                raise forms.ValidationError(msg.format())
            return yr
        else:
            return self.first_year

    def clean_last_year(self):
        """If we can't convert the last_year year value to an integer,
        throw an error"""
        yr = self.cleaned_data["last_year"]
        if yr:
            try:
                yr = int(yr)
            except ValueError:
                msg = "'Last_Year Year' must be numeric."
                raise forms.ValidationError(msg.format())
            return yr
        else:
            return self.last_year

    def clean(self):
        cleaned_data = super(GeoForm, self).clean()

        first_year = cleaned_data.get("first_year")
        last_year = cleaned_data.get("last_year")

        if first_year and last_year:
            if int(first_year) > int(last_year):
                msg = "'First Year' occurs after 'Last Year'."
                raise forms.ValidationError(msg)
        return cleaned_data


class ProjectImageForm(ModelForm):
    class Meta:
        model = ProjectImage
        fields = ("image_path", "caption", "report")
        widgets = {"caption": forms.Textarea(attrs={"rows": 4})}


class EditImageForm(ModelForm):
    class Meta:
        model = ProjectImage
        fields = ("caption", "report")
        widgets = {"caption": forms.Textarea(attrs={"rows": 4})}


class SpatialPointUploadForm(forms.Form):
    """A form for uploading spatial points for a project.
    Accepts only text files (csv or txt) or xlsx files.  A required
    select field determines if the points should replace any that are
    already associated with the project or add to them.

    Most of the code associated wth this form is for the spatial point
    validation - only fields with records than can be successfully
    converted to points that fall within the lake associated with the
    project can be saved.

    """

    points_file = forms.FileField(
        label="Data File",
        required=True,
        validators=[FileExtensionValidator(["csv", "xlsx"])],
    )

    REPLACE_CHOICES = [
        ("replace", "Replace Existing Points"),
        ("append", "Append to Existing Points"),
    ]

    replace = forms.ChoiceField(
        choices=REPLACE_CHOICES, required=True, widget=forms.RadioSelect
    )

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project")
        self.lake_geom = self.project.lake.geom
        super(SpatialPointUploadForm, self).__init__(*args, **kwargs)
        self.fields["points_file"].widget.attrs["class"] = "fileinput"
        self.fields["points_file"].widget.attrs["accept"] = ".csv,.txt,.xlsx"

    def handle_csv_data(self, csv_file):
        # encoding catches the byte-order-mark that can cause issues:
        csv_file = io.TextIOWrapper(csv_file, encoding="utf-8-sig")
        reader = csv.reader(csv_file, delimiter=",", quotechar='"')
        pts = [x for x in list(reader) if x != []]
        for i, row in enumerate(pts):
            pts[i] = [x.replace('"', "") for x in row]

        return pts

    def handle_xlsx_data(self, xlsx_file):
        wb = load_workbook(filename=xlsx_file)
        pts = []

        for row in wb.worksheets[0]:
            pts.append([cell.value for cell in row])
        return pts

    def clean_points_file(self):
        """verify that our file can be parsed, contains the data we think it
        contains, and that the points are actually in the bounding box of the
        lake assoicated with this project.
        """
        validation_errors = []
        geoPoints = None

        points_file = self.cleaned_data.get("points_file", False)
        if points_file:
            if points_file.size > 0.5 * 1024 * 1024:
                raise ValidationError("Points_File file way too large ( > 0.5mb )")

            if points_file.name.endswith("xlsx"):
                pts = self.handle_xlsx_data(points_file.file)
            else:
                pts = self.handle_csv_data(points_file.file)

            MAX_UPLOAD_POINTS = 1000
            if len(pts) > MAX_UPLOAD_POINTS:
                error_msg = (
                    "The points file contains more than {} points! ".format(
                        MAX_UPLOAD_POINTS
                    )
                    + "Reduce the number of points and try again."
                )
                raise ValidationError(error_msg)

            expected_header = ["POINT_LABEL", "DD_LAT", "DD_LON"]
            recieved_header = [x for x in pts.pop(0) if x is not None]

            if not recieved_header == expected_header:
                validation_errors.append(
                    "Malformed header in submitted file."
                    "The header must contain the fields: 'POINT_LABEL', 'DD_LAT' and 'DD_LON'."
                    "The uploaded header is {}".format(
                        ", ".join([f"'{x}'" for x in recieved_header])
                    )
                )

            if not len(pts):
                raise ValidationError(
                    "Points_File does not appear to contain any data!"
                )

            empty_labels = [x for x in pts if x[0] == "" or x[0] is None]
            if len(empty_labels):
                validation_errors.append("At least one point is missing a label")

            try:
                geoPoints = [[x[0], Point(float(x[2]), float(x[1]))] for x in pts]
            except (ValueError, TypeError, IndexError):
                validation_errors.append(
                    "At least one point has an invalid latitude or longitude."
                )

            if geoPoints and self.lake_geom:
                envelope = self.lake_geom.envelope
                out_of_bounds = [x for x in geoPoints if not envelope.contains(x[1])]
                if len(out_of_bounds):
                    msg = """{} of the supplied points are not within the bounds of the lake
                    associated with this project.""".format(
                        len(out_of_bounds)
                    )
                    validation_errors.append(msg)

            if len(validation_errors):
                raise ValidationError(" ".join(validation_errors))
            else:
                return geoPoints
        else:
            raise ValidationError("Couldn't read uploaded points_file")

    def save(self):
        """when we save the form - we need to create a bunch of project sample
        points, and either append them to our project or replace the
        existing ones.

        """
        sample_points = []
        project = self.project
        for pt in self.cleaned_data["points_file"]:
            sample_points.append(SamplePoint(project=project, label=pt[0], geom=pt[1]))

        if self.cleaned_data["replace"] == "replace":
            SamplePoint.objects.filter(project=project).delete()

        SamplePoint.objects.bulk_create(sample_points)

        project.update_multipoints()
        project.update_convex_hull()
