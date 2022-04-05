# E1101 - Class 'whatever' has no 'something' member
# E1120 - No value passed for parameter 'cls' in function call
# pylint: disable=E1101, E1120

# from collections import OrderedDict
import collections

from django.conf import settings
from django.contrib.auth import get_user_model

from django.contrib.gis.db.models import Collect, Union
from django.contrib.gis.geos import MultiPoint
from django.contrib.postgres.search import SearchVectorField, SearchVector
from django.contrib.postgres.indexes import GinIndex

from django.urls import reverse
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.contrib.gis.db import models
from taggit.managers import TaggableManager

from markdown2 import markdown

from common.models import Lake

import datetime
import os
import pytz

from .utils.helpers import get_supervisors, replace_links, strip_carriage_returns

User = get_user_model()

LINK_PATTERNS = getattr(settings, "LINK_PATTERNS", None)
# for markdown2 (<h1> becomes <h3>)
DEMOTE_HEADERS = 2


class ProjectsManager(models.Manager):
    """Custom extensions to the base manager for project objects to
    return approved and completed projects."""

    def get_queryset(self):
        # by default, only return projects that are active:
        return super(ProjectsManager, self).get_queryset().filter(active=True)

    def submitted(self):
        """return a queryset containing only those projects that have been
        submitted, but have not yet been approved or completed.
        """
        return (
            self.prefetch_related("projectmilestones__milestone")
            .filter(
                active=True,
                projectmilestones__milestone__label="Approved",
                projectmilestones__completed__isnull=True,
            )
            .filter(
                projectmilestones__milestone__label="Sign off",
                projectmilestones__completed__isnull=True,
            )
        )

    def approved(self):
        """return a queryset containing only those projects that have been
        approved, but have not been completed or cancelled.
        """
        return (
            self.prefetch_related("projectmilestones__milestone")
            .filter(
                active=True,
                cancelled=False,
                projectmilestones__milestone__label="Approved",
                projectmilestones__completed__isnull=False,
            )
            .filter(
                projectmilestones__milestone__label="Sign off",
                projectmilestones__completed__isnull=True,
            )
        )

    def cancelled(self):
        """return a queryset containing only those projects that have been
        cancelled.
        """
        return self.filter(active=True, cancelled=True)

    def completed(self):
        """return a queryset containing only those projects that have been
        both approved and completed but not cancelled.
        """
        return (
            self.prefetch_related("projectmilestones__milestone")
            .filter(
                active=True,
                cancelled=False,
                projectmilestones__milestone__label="Approved",
                projectmilestones__completed__isnull=False,
            )
            .filter(
                projectmilestones__milestone__label="Sign off",
                projectmilestones__completed__isnull=False,
            )
        )


class ProjectsThisYear(models.Manager):
    """get all of the project objects from the current year"""

    def get_queryset(self):
        # use_for_related_fields = True
        year = datetime.datetime.now().year
        return (
            super(ProjectsThisYear, self)
            .get_queryset()
            .filter(year__gte=year, active=True)
        )


class ProjectsLastYear(models.Manager):
    """get all of the project objects from last year"""

    def get_queryset(self):
        # use_for_related_fields = True
        year = datetime.datetime.now().year - 1
        return (
            super(ProjectsLastYear, self).get_queryset().filter(year=year, active=True)
        )


class MilestoneManager(models.Manager):
    """Sumbitted milestone is created automatically when a project is
    created, and is needed for messages, but is not used anywhere else.
    This manager will auto-matically remove it from the returned
    recordsets.
    """

    def shared(self):
        """
        return only those milestones that are shared among sister
        projects
        """
        return super(MilestoneManager, self).get_queryset().filter(shared=True)

    def get_queryset(self):
        use_for_related_fields = True
        return super(MilestoneManager, self).get_queryset().exclude(label="Submitted")


class MessageManager(models.Manager):
    """
    We only want messages for projects that continue to be active.
    """

    def get_queryset(self):
        use_for_related_fields = True
        return (
            super(MessageManager, self)
            .get_queryset()
            .filter(project_milestone__project__active=True)
        )


class Messages2UsersManager(models.Manager):
    """
    We only want messages for projects that continue to be active.
    """

    def get_queryset(self):
        use_for_related_fields = True
        return (
            super(Messages2UsersManager, self)
            .get_queryset()
            .filter(message__project_milestone__project__active=True)
        )


class Milestone(models.Model):
    """
    Look-up table of reporting milestone and their attributes.  Not all
    milestones will have a report associated with them.  Keeping
    milestones in a separate tables allows us to dynamically add and
    remove milestones associated with individual projects or project
    types (field projects vs synthesis projects).

    Protected is used to limit who can update various milestones.

    """

    id = models.AutoField(primary_key=True)

    # (database, display)
    MILESTONE_CHOICES = {
        ("Core", "core"),
        ("Suggested", "suggested"),
        ("Custom", "custom"),
    }

    label = models.CharField(max_length=50, unique=True, db_index=True)
    label_abbrev = models.CharField(max_length=50, unique=True)
    category = models.CharField(
        max_length=30, choices=MILESTONE_CHOICES, default="Custom"
    )
    report = models.BooleanField(default=False, db_index=True)
    # should this milestone be shared among sister projects?
    shared = models.BooleanField(default=False)
    protected = models.BooleanField(default=False)
    order = models.FloatField(default=99)

    objects = MilestoneManager()
    allmilestones = models.Manager()

    class Meta:
        ordering = ["-report", "order"]

    def __str__(self):
        return self.label


class ProjectType(models.Model):
    """A look-up table to hold project type and attributes of those
    project types. For example - is the project type dependent or
    independent of a fishery, and should there be field data
    associated with it? (E.I. - FN011 and FN121 records)

    """

    id = models.AutoField(primary_key=True)

    PROJECT_SCOPE_CHOICES = {
        ("FD", "Fishery Dependent"),
        ("FI", "Fishery Independent"),
        ("MS", "Multiple Sources"),
    }

    project_type = models.CharField(max_length=150, unique=True, blank=False)
    field_component = models.BooleanField(default=True)
    scope = models.CharField(max_length=30, choices=PROJECT_SCOPE_CHOICES, default="FI")

    class Meta:
        verbose_name = "Project Type"

    def __str__(self):
        """return the project type  as its string representation"""
        return self.project_type


class ProjectProtocol(models.Model):
    """A table to hold our project protocols - allow us to track and
    filter by protocol.

    """

    id = models.AutoField(primary_key=True)

    project_type = models.ForeignKey(
        "ProjectType", related_name="protocols", on_delete=models.CASCADE
    )

    protocol = models.CharField(max_length=150)
    abbrev = models.CharField(max_length=10, unique=True, blank=False)
    deprecated = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "Project Protocol"

    def __str__(self):
        """return the project protocol as its string representation"""
        return "{} ({})".format(self.protocol, self.abbrev)


class Database(models.Model):
    """
    A lookup table to hole list of master databases.
    """

    id = models.AutoField(primary_key=True)

    # thes should be unique!!
    master_database = models.CharField(max_length=250)
    path = models.CharField(max_length=250)

    class Meta:
        verbose_name = "Master Database"

    def __str__(self):
        """return the database name as its string representation"""
        return self.master_database


class FundingSource(models.Model):
    """
    A lookup table to hold the names of the different funding sources
    """

    id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=150, unique=True, blank=False)
    abbrev = models.CharField(max_length=25, unique=True, blank=False)

    class Meta:
        verbose_name = "Funding Source"

    def __str__(self):
        """return the name and abbreviation as its string representation"""
        return "{} ({})".format(self.name, self.abbrev)


class ProjectFunding(models.Model):
    """
    A lookup table to hold the names of the different funding sources
    and how the funding was used.  Originally this data was maintained
    as fields in Project Model.  Moved to a seperate table to
    accomodate multiple funding sources that could be used to fund a
    project.

    """

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey(
        "Project", related_name="funding_sources", on_delete=models.CASCADE
    )

    source = models.ForeignKey(
        "FundingSource", related_name="project_allocations", on_delete=models.CASCADE
    )

    odoe = models.DecimalField(
        "ODOE", max_digits=8, default=0, decimal_places=2, null=True, blank=True
    )
    salary = models.DecimalField(
        "Salary", max_digits=8, default=0, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "Project Funding Source"
        unique_together = ("project", "source")

    def __str__(self):
        """return the funding source as its string representation"""
        return "<{} - {}>".format(self.project.prj_cd, self.source.abbrev)

    @property
    def total(self):
        """the total of funding for the project will be the sum of the salary
        and the odoe.
        """

        salary = self.salary if self.salary else 0
        odoe = self.odoe if self.odoe else 0
        return salary + odoe


class Project(models.Model):
    """
    Class to hold a record for each project
    """

    PROJECT_STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("ongoing", "Ongoing"),
        ("complete", "Complete"),
        ("cancelled", "Cancelled"),
    ]

    status = models.CharField(
        max_length=10,
        choices=PROJECT_STATUS_CHOICES,
        default="submitted",
        db_index=True,
    )

    id = models.AutoField(primary_key=True)

    active = models.BooleanField(default=True)
    cancelled = models.BooleanField(default=False)
    cancelled_by = models.ForeignKey(
        User,
        related_name="CancelledBy",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    signoff_by = models.ForeignKey(
        User, related_name="SignOffBy", on_delete=models.CASCADE, blank=True, null=True
    )

    project_team = models.ManyToManyField(User)

    year = models.CharField(
        "Year", max_length=4, blank=True, editable=False, db_index=True
    )
    prj_date0 = models.DateField("Start Date", blank=False, db_index=True)
    prj_date1 = models.DateField("End Date", blank=False, db_index=True)
    prj_cd = models.CharField("Project Code", max_length=12, unique=True, blank=False)
    prj_nm = models.CharField("Project Name", max_length=60, blank=False)
    prj_ldr = models.ForeignKey(
        User, related_name="ProjectLead", on_delete=models.CASCADE
    )
    field_ldr = models.ForeignKey(
        User, related_name="FieldLead", on_delete=models.CASCADE, blank=True, null=True
    )
    abstract = models.TextField(blank=False, help_text="Project Abstract (public).")
    abstract_html = models.TextField(
        blank=True, null=True, help_text="Project Abstract (public)."
    )

    comment = models.TextField(
        null=True, blank=True, help_text="Comments or Remarks (internal)"
    )
    comment_html = models.TextField(
        blank=True, null=True, help_text="Comments or Remarks (internal)"
    )

    help_str = "Potential risks associated with not running project."
    risk = models.TextField("Risk", null=True, blank=True, help_text=help_str)
    risk_html = models.TextField("Risk", null=True, blank=True, help_text=help_str)

    content_search = SearchVectorField(null=True)

    master_database = models.ForeignKey(
        "Database", on_delete=models.CASCADE, null=True, blank=True
    )
    project_type = models.ForeignKey(
        "ProjectType", on_delete=models.CASCADE, null=True, blank=True
    )

    protocol = models.ForeignKey(
        "ProjectProtocol",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="Projects",
    )

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, related_name="ProjectOwner"
    )
    dba = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=True, related_name="ProjectDBA"
    )

    lake = models.ForeignKey(Lake, on_delete=models.CASCADE, default=1)

    slug = models.SlugField(blank=True, editable=False)
    tags = TaggableManager()

    # managers
    all_objects = models.Manager()
    objects = ProjectsManager()
    last_year = ProjectsLastYear()
    this_year = ProjectsThisYear()

    class Meta:
        ordering = ["-prj_date1"]
        indexes = [GinIndex(fields=["content_search"])]

    def save(self, *args, **kwargs):
        """
        from:http://stackoverflow.com/questions/7971689/
             generate-slug-field-in-existing-table
        Slugify name if it doesn't exist. IMPORTANT: doesn't check to see
        if slug is a dupicate!
        """
        new = False
        if not self.slug or not self.year:
            self.slug = slugify(self.prj_cd)
            # self.year = self.prj_date0.year
            yr = self.prj_cd[6:8]
            self.year = "20" + yr if int(yr) < 50 else "19" + yr
            new = True

        if self.abstract:
            self.abstract = strip_carriage_returns(self.abstract)
            self.abstract_html = markdown(
                self.abstract, extras={"demote-headers": DEMOTE_HEADERS}
            )
            self.abstract_html = replace_links(
                self.abstract_html, link_patterns=LINK_PATTERNS
            )

        if self.comment:
            self.comment = strip_carriage_returns(self.comment)
            self.comment_html = markdown(
                self.comment, extras={"demote-headers": DEMOTE_HEADERS}
            )
            self.comment_html = replace_links(
                self.comment_html, link_patterns=LINK_PATTERNS
            )

        if self.risk:
            self.risk = strip_carriage_returns(self.risk)
            self.risk_html = markdown(
                self.risk, extras={"demote-headers": DEMOTE_HEADERS}
            )
            self.risk_html = replace_links(self.risk_html, link_patterns=LINK_PATTERNS)
        super(Project, self).save(*args, **kwargs)
        if new:
            self.initialize_milestones()

    # @models.permalink
    def get_absolute_url(self):
        """
        return the url for the project
        """

        url = reverse("project_detail", kwargs={"slug": self.slug})
        return url

    def approve(self):
        """
        a helper method to make approving projects easier.  A
        project-milestone object will be created if it doesn't
        exist.
        """
        now = datetime.datetime.now(pytz.utc)

        milestone = Milestone.objects.get(label="Approved")
        projectmilestone, created = ProjectMilestones.objects.get_or_create(
            project=self, milestone=milestone, required=True
        )

        projectmilestone.completed = now
        # save sends pre_save signal
        projectmilestone.save()

        self.status = "ongoing"
        self.save()

    def unapprove(self):
        """
        a helper method to reverse project.approved(), a project-milestone
        object will be created if it doesn't exist."""
        try:
            prjms = ProjectMilestones.objects.get(
                project=self, milestone__label="Approved"
            )
            prjms.completed = None
            # save sends pre_save signal
            prjms.save()

        except ProjectMilestones.DoesNotExist:
            pass
        self.status = "submitted"
        self.save()

    def cancel(self, user):
        """
        a helper method to make approving projects easier.  A
        project-milestone object will be created if it doesn't
        exist.
        """
        now = datetime.datetime.now(pytz.utc)

        milestone = Milestone.objects.get(label="Cancelled")
        projectmilestone, created = ProjectMilestones.objects.get_or_create(
            project=self, milestone=milestone, required=True
        )

        projectmilestone.completed = now
        # save sends pre_save signal
        projectmilestone.save()

        self.status = "cancelled"
        self.cancelled = True
        self.cancelled_by = user
        self.save()

    def uncancel(self):
        """
        a helper method to reverse project.canceld(), a project-milestone
        object will be created if it doesn't exist."""
        try:
            prjms = ProjectMilestones.objects.get(
                project=self, milestone__label="Cancelled"
            )
            prjms.completed = None
            # save sends pre_save signal
            prjms.save()

        except ProjectMilestones.DoesNotExist:
            pass
        self.status = "ongoing"
        self.cancelled = False
        self.cancelled_by = None
        self.save()

    def is_approved(self):
        """Is the current project approved?  Returns true if it is, otherwise
        false."""
        approved = ProjectMilestones.objects.filter(
            project=self, milestone__label="Approved"
        ).first()
        if approved is None:
            return False

        if approved.completed is not None:
            return True
        else:
            return False

    def signoff(self, user):
        """A helper function to make it easier to sign off a project"""
        # TODO - add logic here to make sure all previous requirements
        # have been met! - can't signoff on a project that wasn't
        # approved or completed.

        now = datetime.datetime.now(pytz.utc)
        milestone = Milestone.objects.get(label__iexact="Sign Off")
        prjms, created = ProjectMilestones.objects.get_or_create(
            project=self, milestone=milestone
        )
        prjms.completed = now
        prjms.save()

        self.signoff_by = user
        self.status = "complete"
        self.save()

    def reopen(self):
        """A helper function to reopen a project.  This does not keep track of
        whether or not the project had been previously closed or how many
        times it has been closed or re-activated."""

        milestone = Milestone.objects.get(label__iexact="Sign Off")
        prjms, created = ProjectMilestones.objects.get_or_create(
            project=self, milestone=milestone
        )
        prjms.completed = None
        self.status = "ongoing"
        prjms.save()

    def is_complete(self):
        """Is the current project completed (ie. signoff=True)?  Returns true
        if it is, otherwise false.
        """
        try:
            completed = ProjectMilestones.objects.get(
                project=self, milestone__label__iexact="Sign Off"
            )
        except ProjectMilestones.DoesNotExist:
            return False

        if completed.completed is not None:
            return True
        else:
            return False

    def _get_status(self):
        """
        The status of a project must be one of:

        + Submitted - not approved
        + Ongoing - approved, but not cancelled or signed off
        + Cancelled - cancelled==True
        + Complete - signoff==True

        NOTE - projects cannot be completed or cancelled withouth being
        approved first!  Similarly, cancelled projects cannot be completed.

        """

        if self.cancelled:
            return "Cancelled"
        elif self.is_complete():
            return "Complete"
        elif not self.is_approved():
            return "Submitted"
        else:
            return "Ongoing"

    def project_suffix(self):
        """
        return the prject suffix for the given project"""

        return self.prj_cd[-3:]

    def name(self):
        """
        alias for prj_nm - maintains fishnetII name in model but works
         with django convention of obj.name."""

        return self.prj_nm

    def description(self):
        """
        alias for comment - maintains fishnetII comment in model but works
         with django convention of obj.description."""

        return self.abstract

    def __str__(self):
        """
        Return the name of the project and it's project code"""

        ret = "%s (%s)" % (self.prj_nm, self.prj_cd)
        return ret

    def get_milestones(self, required=True):
        """
        get all of the milestone events that have been assigned to
        this project - (these are just milestone events where report==False)"""

        if required is True:
            return (
                ProjectMilestones.objects.filter(
                    project=self, required=True, milestone__report=False
                )
                .order_by("milestone__order")
                .select_related("project", "milestone")
            )
        else:
            return (
                ProjectMilestones.objects.filter(project=self, milestone__report=False)
                .order_by("milestone__order")
                .select_related("project", "milestone")
            )

    def get_reporting_requirements(self):
        """
        get all of the reports have been assigned to
        this project - no distinction between core or custom reports"""

        return (
            ProjectMilestones.objects.filter(project=self, milestone__report=True)
            .order_by("milestone__order")
            .select_related("project", "milestone")
        )

    def get_uploaded_reports(self):
        """
        get all of the CURRENT reports that are associated with this
        project.  Non-current reports are not included in this
        recordset.
        """

        # TODO Filter for report=True
        return Report.objects.filter(current=True, projectreport__project=self)

    def get_associated_files(self):
        """
        get all of the associated files associated with this project
        Associated files are not associated with a milesone and are
        likely to be different for each project..

        """

        return AssociatedFile.objects.filter(project=self)

    def get_core_assignments(self, all_reports=True):
        """
        get all of the core reports have been assigned to this project, if
        'all_reports' is true, all assignements are returned, if 'all_reports'
        is False, only required assignments are returned.

        """

        if all_reports is True:
            assignments = self.get_reporting_requirements().filter(
                milestone__category="Core", milestone__report=True
            )
        else:
            assignments = (
                self.get_reporting_requirements()
                .filter(milestone__category="Core", milestone__report=True)
                .filter(required=True)
            )
        return assignments

    def get_milestone_status_dict(self):
        """
        In order to impoved the performance of the myProjects view we
        need a function that will take a project return a dictionary of
        milestones the keys of the dictionary will be the abbreviated label
        of the milestone, in lower case with spaces replaced by dashes.  the
        value of each dictionary key will be the status of the milestone:

        + required-done
        + required-notDone
        + notRequired-done
        + notRequired-notDone

        The status of all custom reports is tacked on to the end of
        the ordered dictionary and reflects the status of all required
        additional reporting requirements.

        """

        milestone_status = collections.OrderedDict()

        # we need to instantiate an order dictionary that has all of
        # the milestone keys - ensures that they are reported for every
        # project (and in the same order) - without this, some of our
        # rows will have different lengths.

        all_milestones = (
            Milestone.objects.filter(category="Core").order_by("order").all()
        )
        for ms in all_milestones:
            key = ms.label_abbrev.lower().replace(" ", "-")
            milestone_status[key] = {
                "status": None,
                "type": "report" if ms.report else "milestone",
            }

        milestones = (
            self.projectmilestones.filter(milestone__category="Core")
            .exclude(milestone__label="Submitted")
            .select_related("milestone")
            .order_by("milestone__order")
            .all()
        )

        for ms in milestones:
            key = ms.milestone.label_abbrev.lower().replace(" ", "-")
            if ms.required:
                value = {
                    "status": ("required-done" if ms.completed else "required-notDone"),
                    "type": "report" if ms.milestone.report else "milestone",
                }
            else:
                value = {
                    "status": (
                        "notRequired-done" if ms.completed else "notRequired-notDone"
                    ),
                    "type": "report" if ms.milestone.report else "milestone",
                }

            milestone_status[key] = value

        # finally for each project, we need to know if this project has any
        # custom reporting requirements and their status:
        milestones = self.projectmilestones.select_related("milestone").filter(
            milestone__category="custom"
        )
        if not milestones:
            milestone_status["custom"] = {
                "status": "notRequired-notDone",
                "type": "report",
            }
        else:
            # if the status of all custom milestones are complete then
            # required-done else 'required-notDone'
            done = [x.completed is not None for x in milestones if x.required == True]
            if all(x == True for x in done):
                milestone_status["custom"] = {
                    "status": "required-done",
                    "type": "report",
                }
            else:
                milestone_status["custom"] = {
                    "status": "required-notDone",
                    "type": "report",
                }
        return milestone_status

    def get_custom_assignments(self):
        """get a list of any custom reports that have been assigned to
        this project"""
        return (
            self.get_reporting_requirements()
            .filter(required=True, milestone__report=True)
            .exclude(milestone__category="Core")
        )

    def get_complete(self):
        """
        get the project reports that have uploaded reports
        associated with them."""

        # TODO Filter for report=True
        return ProjectMilestones.objects.filter(project=self).filter(
            report__in=Report.objects.filter(current=True, projectreport__project=self)
        )

    def get_outstanding(self):
        """
        these are the required reports that have not been submitted yet"""

        # TODO Filter for report=True
        return ProjectMilestones.objects.filter(
            project=self, milestone__report=True
        ).exclude(report__in=Report.objects.filter(projectreport__project=self))

    def get_milestone_dicts(self):
        """
        return a dictionary of dictionaries containing elements of
        all milestones, core and custom reports as well as vectors indicating
        which ones have been assigned to this project."""

        # TODO Filter for report=True

        # get a queryset of all reports we consider 'core'
        milestones = Milestone.objects.filter(report=False)
        corereports = Milestone.objects.filter(category="Core", report=True)
        customreports = Milestone.objects.filter(category="Custom", report=True)

        # we need to convert the querset to a tuple of tuples
        milestones = tuple([(x[0], x[1]) for x in milestones.values_list()])
        corereports = tuple([(x[0], x[1]) for x in corereports.values_list()])
        customreports = tuple([(x[0], x[1]) for x in customreports.values_list()])

        # get the milestones currently assigned to this project, if not return a
        # dictionary with all reports assigned
        milestones_assigned = self.get_milestones()
        milestones_assigned = [x.milestone_id for x in list(milestones_assigned)]

        core_assigned = self.get_core_assignments()
        core_assigned = [x.milestone_id for x in list(core_assigned)]

        custom_assigned = self.get_custom_assignments()
        custom_assigned = [x.milestone_id for x in list(custom_assigned)]

        # put the reports and assigned reports in a dictionary
        milestones = dict(milestones=milestones, assigned=milestones_assigned)
        core = dict(milestones=corereports, assigned=core_assigned)
        custom = dict(milestones=customreports, assigned=custom_assigned)

        milestones_dict = dict(Milestones=milestones, Core=core, Custom=custom)

        return milestones_dict

    def milestone_complete(self, milestone):
        """
        This is a helper function used in to manage project reporting
        requirements. It returns True if the milestone has been
        completed for a project, it returns False if a require element
        has not been completed, and returns None if the milestone does
        not exist or was not requested for this project.

        Arguments:
        - `self`: a project object
        - `milestone`: a milestone object

        """

        try:
            pms = ProjectMilestones.objects.get(project=self, milestone=milestone)
            if pms.completed:
                # - requested, done = True
                # - not requested, done anyway = True
                return True
            elif pms.required:
                # -requested, not done = False
                return False
            else:
                # -not requested, not done - None
                return None
        except (ProjectMilestones.DoesNotExist, ValueError) as e:
            return None

    def initialize_milestones(self):
        """
        A function that will add a record into "ProjectMilestones" for
        each of the core reports and milestones for newly created projects"""

        corereports = Milestone.allmilestones.filter(category="Core")
        for report in corereports:
            if report.label == "Submitted":
                now = datetime.datetime.now(pytz.utc)
            else:
                now = None
            ProjectMilestones.objects.get_or_create(
                project=self, milestone=report, completed=now
            )

    def get_family(self):
        """
        If this project belongs to a familiy (i.e. - has sisters) return
        the family, otherwise return None."""

        try:
            family = Family.objects.get(projectsisters__project=self)
        except Family.DoesNotExist:
            family = None
        return family

    def add_sister(self, slug):
        """
        Add the project identified by slug to the familiy of the current
        project.  If the current project, doesn't belong to a family, create
        it first then add the sister.
        """

        family = self.get_family()
        if family is None:
            family = Family.objects.create()
            ProjectSisters.objects.create(project=self, family=family)

        # now add the project associated with slug to family:
        project = Project.objects.get(slug=slug)
        ProjectSisters.objects.create(project=project, family=family)

    def get_sisters(self, excludeself=True):
        """
        Return a queryset of sister projects associated with this
        project. - By default, the current project is not incuded in
        the recordset"""

        family = self.get_family()
        if family:
            try:
                if excludeself:
                    sisters = (
                        Project.objects.filter(projectsisters__family=family)
                        .exclude(slug=self.slug)
                        .order_by("prj_cd")
                    )
                else:
                    sisters = Project.objects.filter(projectsisters__family=family)
            except Project.DoesNotExist:
                sisters = []
        else:
            sisters = []
        return sisters

    def has_sister(self):
        """
        a simple little helper function - returns True if this project has
        one or more sisters, False otherwise.  Used in templates to
        issue warnings about cascading effects on other projects.
        """

        if len(self.get_sisters()):
            return True
        else:
            return False

    def get_sister_candidates(self):
        """
        return a querset of projects that could be sisters to this
        project.  To be a candidates for sisterhood, a project must be
        approved, be the same project type, run in the same year and
        not be a sister to another project. If the current project
        isn't approved, no candidates will be returned regardless."""

        if self.is_approved():
            try:
                candidates = (
                    Project.objects.approved()
                    .filter(
                        project_type=self.project_type,
                        protocol=self.protocol,
                        lake=self.lake,
                        year=self.year,
                        projectsisters__isnull=True,
                    )
                    .exclude(slug=self.slug)
                    .order_by("slug")
                )
            except Project.DoesNotExist:
                candidates = []
        else:
            candidates = []
        return candidates

    def delete_sister(self, slug):
        """
        remove the project identified by "slug" from the familiy associated
        with this project.  If this project is now the only member of
        teh familiy, delete the family so we don't end-up with a bunch
        of single member families.
        """

        project = Project.objects.get(slug=slug)
        ProjectSisters.objects.filter(project=project).delete()
        family = self.get_family()
        # if this was the last sibling in the family get rid of its
        # record and the family record too.
        familysize = ProjectSisters.objects.filter(family=family).count()
        if familysize == 1:
            ProjectSisters.objects.filter(family=family).delete()
            Family.objects.filter(id=family.id).delete()

    def disown(self):
        """
        the special case when we want to remove this project from an
        existing family, but keep the other sister relationships intact."""

        family = self.get_family()

        self.delete_sister(self.slug)
        # if this was the last sibling in the family get rid of it too.
        familysize = ProjectSisters.objects.filter(family=family.id).count()
        if familysize == 1:
            ProjectSisters.objects.filter(family=family).delete()
            Family.objects.filter(id=family.id).delete()

    def get_sample_points(self):
        """
        get the coordinates of sample points associated with this
        project.  Returns a list of tuples.  Each tuple contains the
        sample id, dd_lat and dd_lon

        """

        points = SamplePoint.objects.filter(project__id=self.id).values_list(
            "label", "geom"
        )

        return points

    def update_multipoints(self):
        """
        get the coordinates of sample points associated with this
        project.  Returns a list of tuples.  Each tuple contains the
        sample id, dd_lat and dd_lon

        """

        # see if there already is a polygon, if not create one
        try:
            project_points = self.multipoints
        except ProjectMultiPoints.DoesNotExist:
            project_points = ProjectMultiPoints(project=self)

        points = self.get_sample_points()
        if points:
            try:
                multipoints = points.aggregate(pts=Union("geom")).get("pts")
            except:
                if hasattr(self, "multipoints"):
                    self.multipoints.delete()
                    self.save()
                else:
                    return None

            if multipoints.geom_type == "Point":
                # there was only one point and we need to cast it to a multipoint:
                project_points.geom = MultiPoint(multipoints)
            else:
                project_points.geom = multipoints
            project_points.save()
        else:
            # if there are no points, there should be not be a project points record
            # associated with this project if there was one originally
            # or not.
            if project_points.id:
                self.multipoints.delete()
                self.save()
                return self
            else:
                project_points = None

    def update_convex_hull(self):
        """
        A method to update the assocaited table containing the project
        polygon object.  If there are points, get or create a polygon
        object.  If there aren't any points, or the points don't form
        a polygon, don't create a polygon object, or delete one if it
        exists.

        Arguments:
        - `self`:

        """

        # see if there already is a polygon, if not create one
        try:
            project_poly = self.convex_hull
        except ProjectPolygon.DoesNotExist:
            project_poly = ProjectPolygon(project=self)

        points = self.get_sample_points()
        if points:
            try:
                points = points.aggregate(Collect("geom")).get("geom__collect")
                convex_hull = points.convex_hull
            except:

                if hasattr(self, "convex_hull"):
                    self.convex_hull.delete()
                    self.save()
                else:
                    return None

            if convex_hull.geom_type == "Polygon":
                project_poly.geom = convex_hull
                project_poly.save()
            else:
                if project_poly.id:
                    self.convex_hull.delete()
                    self.save()
                else:
                    project_poly = None

        else:
            # import pdb;pdb.set_trace()
            # if there are no points, there should be not be a polygon
            # associated with this project if there was one originally
            # or not.
            if project_poly.id:
                self.convex_hull.delete()
                self.save()
                return self
            else:
                project_poly = None

        # see if there are any sample points:
        # if so, create a polygon object.

        # see if there is already a polygon object for this
        # project. If so, update it with our new polygon, if not
        # create it, with the new polygon object.  If there is a
        # polygon object but we can't create one with the current
        # points, delete the old record.

    # can we create a polygon from existing points?

    @property
    def total_odoe(self):
        """
        Return the total odoe for this project from all sources.
        """

        return sum([x.odoe for x in self.funding_sources.all()])

    @property
    def total_salary(self):
        """
        Return the total salary for this project from all sources.
        """

        return sum([x.salary for x in self.funding_sources.all()])

    @property
    def total_cost(self):
        """
        A little helper function to calculate the total cost of a project
        (sum of salary and odoe)
        """

        return sum([(x.salary + x.odoe) for x in self.funding_sources.all()])


class SamplePoint(models.Model):
    """
    A class to hold the sampling locations of a :model:`Project`.  In most
    cases, a SamplePoint instance represents a net in the water, but
    can have different meaning for different projects.
    """

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey("Project", on_delete=models.CASCADE)
    label = models.CharField(max_length=60, null=True, blank=True)
    geom = models.PointField(
        srid=4326, help_text="Represented as (longitude, latitude)"
    )

    # project code and sample number or space name:
    # dd_lat
    # dd_lat
    # popup_html = models.TextField()

    objects = models.Manager()

    class Meta:
        indexes = [models.Index(fields=["project", "geom"])]

    @property
    def dd_lat(self):
        return self.geom.y

    @property
    def dd_lon(self):
        return self.geom.x

    @property
    def popup_text(self):
        """
        Pop-up text should include a hyperlink to project detail so that
        when we find projects by region, the leaflet map will provide
        us with a way to get more inforamtion about specific net
        sets.
        """
        return str(self)

    def __str__(self):
        """
        Return a string that include the project code and label
        """
        if self.label:
            return "{} - {}".format(self.project.prj_cd, self.label)
        else:
            return "{}".format(self.project.prj_cd)


class ProjectImage(models.Model):
    """
    A class to hold images of our projects.  Each image has a foreign key back
    to :model:`pjtk2.Project`.
    """

    def get_image_path(self, image_path):
        """
        A little helper function used by "upload_to" for pictures.
        It will save all of the images associated with a project in a project
        specific directory (named using the project code)
        """

        val = "project_images/{}/{}".format(self.project.prj_cd, image_path)
        return val

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="images"
    )
    order = models.IntegerField("the order that the images are presented", default=0)
    image_path = models.ImageField(upload_to=get_image_path)
    caption = models.CharField("figure caption", max_length=1000)
    report = models.BooleanField(
        "should this image be included in the annual report too?", default=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        """
        Arguments:
        - `self`:
        """
        return "{} - {}".format(self.project, self.caption)


class ProjectMultiPoints(models.Model):
    """A class/table to hold all of the spatial points in a project. A 1:1
    relationship between prjects and the multi point record. Used for
    spatil searches - accounts for cases with where a convex hull
    cannot be calcualted because there is one or two points.  intesect
    and contains can still be used.

    """

    id = models.AutoField(primary_key=True)

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="multipoints"
    )
    geom = models.MultiPointField(srid=4326)

    objects = models.Manager()

    def __str__(self):
        """
        Return a string that include the project code
        """
        return "<{}>".format(self.project.prj_cd)


class ProjectPolygon(models.Model):
    """
    A class to hold the convex hull derived from the sampling locations
    of a project.  Calculated when sample points are uploaded into
    project tracker.  Makes spatial queries much faster - query few
    polygons instead of lots and lots of individual points.

    """

    id = models.AutoField(primary_key=True)

    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="convex_hull"
    )
    geom = models.PolygonField(srid=4326)

    objects = models.Manager()

    def __str__(self):
        """
        Return a string that include the project code
        """
        return "<{}>".format(self.project.prj_cd)


class ProjectMilestones(models.Model):
    """
    List of reporting requirements for each project
    """

    id = models.AutoField(primary_key=True)

    # aka - project milestones
    project = models.ForeignKey(
        "Project", related_name="projectmilestones", on_delete=models.CASCADE
    )
    # report_type = models.ForeignKey('Milestone')
    milestone = models.ForeignKey(
        "Milestone", related_name="projectmilestones", on_delete=models.CASCADE
    )
    required = models.BooleanField(default=True, db_index=True)
    completed = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        # unique_together = ("project", "report_type",)
        unique_together = ("project", "milestone")
        verbose_name_plural = "Project Milestones"

    def __str__(self):
        """Return a string that include the project code and milestone label"""
        return "%s - %s" % (self.project.prj_cd, self.milestone.label)


class Report(models.Model):
    """
    A class for reports.  A single report can be linked to multiple
    entries in Project Reports"""

    id = models.AutoField(primary_key=True)

    current = models.BooleanField(default=True)
    projectreport = models.ManyToManyField("ProjectMilestones")

    report_path = models.FileField(upload_to="milestone_reports/", max_length=200)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    # uploaded_by = models.CharField(max_length = 300)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    report_hash = models.CharField(max_length=300)

    def __str__(self):
        """Use the file path as the string representation of a report"""
        return str(self.report_path)


class AssociatedFile(models.Model):
    """class for associated files.  Unlike reports, an associated file can
    only be linked to a single project
    """

    def get_associated_file_upload_path(self, filename):
        """a little helper function used by "upload_to" of associated files.
        It will save all of the files associated with a project in a project
        specific directory (named using the project code)
        """
        val = os.path.join("associated_files", self.project.prj_cd, filename)
        return val

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    file_path = models.FileField(
        upload_to=get_associated_file_upload_path, max_length=200
    )
    current = models.BooleanField(default=True)
    uploaded_on = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    hash = models.CharField(max_length=300)

    def __str__(self):
        """Use the file path as the string representation of a report"""
        return str(self.file_path)

    # def get_project_code(self):
    #    '''return the project code of the project this file is associated
    #    with.  Used to build upload_to path'''
    #    pass


class Bookmark(models.Model):
    """a class to allow users to bookmark and unbookmark their
    favourite projects."""

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="project_bookmark"
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="unique_user_project_bookmark"
            )
        ]

    def __str__(self):
        """return the name of the associated project as our representation"""
        return "%s" % self.project

    def get_watchers(self):
        """Return the list of user who are currently watching a particular
        project"""
        bookmarks = Bookmark.objects.filter(project=self.project)
        watchers = [x.user for x in bookmarks]
        return watchers

    def get_project_url(self):
        """Use the url of the project for the bookmark too."""
        return self.project.get_absolute_url()

    def name(self):
        """Use the project name for the bookmark too."""
        return self.project.prj_nm

    def get_project_code(self):
        """Use the project code for the bookmark too."""
        return self.project.prj_cd

    def project_type(self):
        """Use the project type for the bookmark too."""
        return self.project.project_type

    def prj_ldr(self):
        """Use the project leader for the bookmark too."""
        return self.project.prj_ldr

    def year(self):
        """Use the project year for the bookmark too."""
        return self.project.year


class Family(models.Model):
    """Provides a mechanism to ensure that families are unique and
    auto-created.  The relationship between projects and families is
    essentailly an m2m, but currently djagno does not provide a
    mechanism to ensure that each project is associated with just one
    family."""

    id = models.AutoField(primary_key=True)

    class Meta:
        verbose_name_plural = "Families"

    def __str__(self):
        """A simple string representation"""
        return str("Family %s" % self.id)


class ProjectSisters(models.Model):
    """Sister projects have common presentations and summary reports.
    They must be the same project type, and run in the same year."""

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey("Project", on_delete=models.CASCADE)
    family = models.ForeignKey("Family", on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Project Sisters"
        ordering = ["family", "project"]

    def __str__(self):
        """Return the project and family as a string"""
        return str("Project - %s - Family %s" % (self.project, self.family))


class EmployeeManager(models.Manager):
    """the default manager for employees will only return active users."""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("user", "supervisor__user")
            .filter(user__is_active=True)
            .order_by("user__username")
        )


class Employee(models.Model):
    """The employee model is an extension to the user model that captures
    the hierachical employee-supervisor relationship between users."""

    ROLL_CHOICES = {("manager", "Manager"), ("dba", "DBA"), ("employee", "Employee")}

    id = models.AutoField(primary_key=True)

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")
    # user = models.ForeignKey(User, unique=True, related_name='employee')
    position = models.CharField(max_length=60)
    role = models.CharField(
        max_length=30, choices=ROLL_CHOICES, default="Employee", db_index=True
    )
    lake = models.ManyToManyField(Lake)
    supervisor = models.ForeignKey(
        "self", on_delete=models.CASCADE, blank=True, null=True
    )
    # supervisor = models.ForeignKey(User, unique=False, blank=True, null=True,
    #                               related_name='supervisor')

    # to do - add custom manager to return all emplyees and just active employees
    # return all species for admin page, tagged species by default
    all_objects = models.Manager()
    objects = EmployeeManager()

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        """Use the username of the Employee as the string representation"""
        return self.user.username

    def get_lakes(self):
        return ", ".join([l.lake_name for l in self.lake.all()])


class Message(models.Model):
    """A table to hold all of our messages and which project and milestone
    they were associated with."""

    id = models.AutoField(primary_key=True)

    # (database, display)
    distribution_list = models.ManyToManyField(User, through="Messages2Users")

    msgtxt = models.CharField(max_length=100)
    project_milestone = models.ForeignKey(ProjectMilestones, on_delete=models.CASCADE)
    # these two fields will allow us to keep track of why messages were sent:

    # we will need a project 'admin' to send announcements
    # "Notification system is now working."
    # "Feature Request/Bug Reporting has been implemented."

    LEVEL_CHOICES = {("info", "Info"), ("actionrequired", "Action Required")}

    level = models.CharField(max_length=30, choices=LEVEL_CHOICES, default="info")

    objects = MessageManager()

    def __str__(self):
        """return the messsage as it's unicode method."""
        return self.msgtxt


class Messages2Users(models.Model):
    """a table to associated messages with users and keep track of when
    they were create and when they were read."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    read = models.DateTimeField(blank=True, null=True, db_index=True)

    objects = Messages2UsersManager()

    class Meta:
        unique_together = ("user", "message")
        verbose_name_plural = "Messages2Users"

    def __str__(self):
        """return the messsage as it's unicode method."""
        return "%s - %s" % (self.user, self.message)

    def mark_as_read(self):
        self.read = datetime.datetime.now(pytz.utc)
        self.save()


# =========================
#   Message functions


def build_msg_recipients(project, level=None, dba=True, ops=True):
    """A function to complile the list of recipients for messages

    project - a project instance
    level - an integer indicating how high up the employee hierarchy the
             message should propegate (not yet implemented)
    dba - should the project's dba be notified too?
    ops - should the designated operations coordinator(s) be nofitied
             (also not yet implemented)
    The function returns a list of unique user instances.
    """

    prj_owner = project.owner
    prj_owner = Employee.objects.get(user__id=prj_owner.id)
    recipients = get_supervisors(prj_owner)
    # convert the employees to user objects
    recipients = [x.user for x in recipients]

    if level and level < len(recipients):
        # trim the list of supervisors here (if appropriate)
        recipients = recipients[: -(level - 1)]
    # Find out who is watching this project and add them to the list too
    bookmarks = Bookmark.objects.filter(project=project)
    if bookmarks.exists():
        for watcher in bookmarks:
            recipients.append(watcher.user)
    # send notice to dba too
    if dba:
        recipients.append(project.dba)
    if ops:
        # recipients.append(project.ops)
        pass
    # remove any duplicates
    recipients = list(set(recipients))
    return recipients


def send_message(msgtxt, recipients, project, milestone):
    """Create a record in the message database and send it to each user in
    recipients by appending a record to Messages2Users for each one."""

    # if the Project Milestone doesn't exist for this project and
    # milestone create it
    prjms, created = ProjectMilestones.objects.get_or_create(
        project=project, milestone=milestone
    )

    # create a message object using the message text and the project-milestone
    message = Message.objects.create(msgtxt=msgtxt, project_milestone=prjms)
    # then loop through the list of recipients and add one record to
    # Messages2Users for each one:
    try:
        for recipient in recipients:
            # user = User.objects.get(Employee=emp)
            # Messages2Users.objects.create(user=recipient, msg=message)
            msg4u = Messages2Users(user=recipient, message=message)
            msg4u.save()
    except TypeError:
        # Messages2Users.objects.create(user=recipients, msg=message)
        msg4u = Messages2Users(user=recipients, message=message)
        msg4u.save()


# =====================================
#    Signals

# TODO Complete the pre_save signal to ProjectMilestones - send
# message to appropriate people whenever a record in this table is
# added or updated.


@receiver(pre_save, sender=ProjectMilestones)
def send_notice_prjms_changed(sender, instance, **kwargs):
    """If the status of a milestone has changed, send a message to the
    project lead, their supervisor, the data custodian (and perhaps
    someday, the operations team).  Note that 'submitted' milestone
    need to be handled using a post_save signal.
    """

    msgtxt = ""

    try:
        original = ProjectMilestones.objects.get(pk=instance.pk)
    except ProjectMilestones.DoesNotExist:
        # in this case, there was no original.
        original = None

    # if we found an original projectmilestone,
    if original:
        # find out if 'completed' has changed and whether or not it is now
        # empty and build an appropriate message
        if instance.completed != original.completed and instance.completed:
            # this milestone has been satisfied
            msgtxt = instance.milestone.label

        elif instance.completed != original.completed and original.completed:
            # this milestone has been 'un-approved'
            msgtxt = "The milestone '%s' has been revoked" % instance.milestone.label
    if msgtxt:
        # build the list of people we will be sending the message to
        recipients = build_msg_recipients(instance.project)
        send_message(
            msgtxt, recipients, project=instance.project, milestone=instance.milestone
        )


# pre_save.connect(send_notice_prjms_changed, sender=ProjectMilestones)


@receiver(post_save, sender=ProjectMilestones)
def send_notice_project_submitted(sender, instance, **kwargs):
    """If the status of a milestone has changed, send a message to the
    project lead, their supervisor, the data custodian (and perhaps
    someday, the operations team).  Note that 'submitted' milestone
    need to be handled using a post_save signal.
    """

    if instance.milestone.label == "Submitted":
        msgtxt = "Submitted"
        recipients = build_msg_recipients(instance.project)
        send_message(
            msgtxt, recipients, project=instance.project, milestone=instance.milestone
        )
