import factory
from datetime import datetime
from django.contrib.auth import get_user_model
from django.template.defaultfilters import slugify
from django.contrib.gis.geos import GEOSGeometry

from pjtk2.models import *
from common.models import Lake

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = "John"
    last_name = "Doe"
    # username = 'johndoe'
    username = factory.Sequence(lambda n: "User {0}".format(n))
    email = "johndoe@hotmail.com"
    # admin = False
    password = "Abcd1234"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default ``_create`` with our custom call."""
        manager = cls._get_manager(model_class)
        # The default would use ``manager.create(*args, **kwargs)``
        return manager.create_user(*args, **kwargs)


class DBA_Factory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = "Bill"
    last_name = "Gates"
    # username = 'billgates'
    username = factory.Sequence(lambda n: "DBA {0}".format(n))
    email = "microsoft@sucks.com"
    is_superuser = True
    is_active = True

    #    @classmethod
    #    def _prepare(cls, create, **kwargs):
    #        password = kwargs.pop('password', None)
    #        user = super(DBA_Factory, cls)._prepare(create, **kwargs)
    #        if password:
    #            user.set_password(password)
    #            if create:
    #                user.save()
    #        return user

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default ``_create`` with our custom call."""
        manager = cls._get_manager(model_class)
        # The default would use ``manager.create(*args, **kwargs)``
        return manager.create_user(*args, **kwargs)


class ManagerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = "Boss"
    last_name = "Hogg"
    username = "bosshogg"
    email = "bosshogg@hotmail.com"
    # manager = True

    #    @classmethod
    #    def _prepare(cls, create, **kwargs):
    #        password = kwargs.pop('password', None)
    #        user = super(DBA_Factory, cls)._prepare(create, **kwargs)
    #        if password:
    #            user.set_password(password)
    #            if create:
    #                user.save()
    #        return user

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default ``_create`` with our custom call."""
        manager = cls._get_manager(model_class)
        # The default would use ``manager.create(*args, **kwargs)``
        return manager.create_user(*args, **kwargs)


class LakeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lake
        django_get_or_create = ("abbrev",)

    lake_name = "Lake Huron"
    abbrev = "HU"


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee

    user = factory.SubFactory(UserFactory)
    position = "worker bee"
    role = "employee"
    # lake = factory.SubFactory(LakeFactory)
    supervisor = None


class ProjTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectType
        django_get_or_create = ("project_type",)

    project_type = "Offshore Index"
    scope = "FI"


class ProjProtocolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectProtocol
        django_get_or_create = ("abbrev",)

    project_type = factory.SubFactory(ProjTypeFactory)
    protocol = "Broad Scale Monitoring"
    abbrev = "BSM"


class DatabaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Database

    master_database = "Offshore Master"
    path = "C:/Path/to/somedb.mdb"


class FamilyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Family

    id = factory.Sequence(lambda n: n)


class ProjectFactory(factory.django.DjangoModelFactory):
    """year and slug are built by the project save method"""

    class Meta:
        model = Project

    prj_cd = "LHA_IA12_123"
    prj_nm = "Fake Project"
    # prj_ldr = "Bob Sakamano"
    prj_ldr = factory.SubFactory(UserFactory)
    field_ldr = factory.SubFactory(UserFactory)
    abstract = "This is the abstract for a fake project"
    comment = "This is a comment for our fake project"
    risk = "none"
    project_type = factory.SubFactory(ProjTypeFactory)
    protocol = factory.SubFactory(ProjProtocolFactory)
    master_database = factory.SubFactory(DatabaseFactory)
    owner = factory.SubFactory(UserFactory)
    dba = factory.SubFactory(DBA_Factory)

    lake = factory.SubFactory(LakeFactory)

    @factory.lazy_attribute
    def prj_date0(self):
        """
        create the start date from the project code
        """
        yr_string = self.prj_cd[6:8]
        year = "19" + yr_string if int(yr_string) > 50 else "20" + yr_string
        datestring = "January 15, {0}".format(year)
        prj_date0 = datetime.datetime.strptime(datestring, "%B %d, %Y")
        return prj_date0

    @factory.lazy_attribute
    def prj_date1(self):
        """
        create the end date from the project code
        """
        yr_string = self.prj_cd[6:8]
        year = "19" + yr_string if int(yr_string) > 50 else "20" + yr_string
        datestring = "January 16, {0}".format(year)
        prj_date1 = datetime.datetime.strptime(datestring, "%B %d, %Y")
        return prj_date1

    @factory.lazy_attribute
    def year(self):
        """
        calculate a based on project code
        """

        yr_string = self.prj_cd[6:8]
        year = "19" + yr_string if int(yr_string) > 50 else "20" + yr_string
        return year


class ProjectImageFactory(factory.django.DjangoModelFactory):
    """
    A factory to create fake images for our projects.
    """

    class Meta:
        model = ProjectImage

    project = factory.SubFactory(ProjectFactory)
    order = factory.Sequence(lambda n: n)
    image_path = factory.Sequence(lambda n: "FakeImage-{}.png".format(n))
    caption = "Image caption placeholder"
    alt_text = "Image alt text placeholder"
    report = True


class ProjectSisters(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectSisters

    family = factory.SubFactory(FamilyFactory)
    project = factory.SubFactory(ProjectFactory)


class MilestoneFactory(factory.django.DjangoModelFactory):
    """
    Look-up table of reporting milestones
    """

    class Meta:
        model = Milestone
        django_get_or_create = ("label",)

    label = "Completion Report"
    label_abbrev = factory.Sequence(lambda n: "milestone {0}".format(n))
    shared = False
    category = "Core"
    order = 1


class FundingSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FundingSource

    """Funding Source(s)"""

    name = "Special Purpose Account"
    abbrev = "spa"


class ProjectFundingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectFunding

    """Funding Source(s) for each project"""

    project = factory.SubFactory(ProjectFactory)
    source = factory.SubFactory(FundingSourceFactory)

    odoe = 1000
    salary = 5000


class ProjectMilestonesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectMilestones
        django_get_or_create = ("project", "milestone")

    """list of reporting requirements for each project"""
    project = factory.SubFactory(ProjectFactory)
    milestone = factory.SubFactory(MilestoneFactory)


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    current = True
    # projectreport = factory.SubFactory(ProjectMilestonesFactory)
    report_path = "some/fake/file.txt"
    # uploaded_by = "Bob"
    uploaded_by = factory.SubFactory(UserFactory)
    report_hash = "1234"

    # @factory.post_generation
    # def projectreport(self, create, extracted, **kwargs):
    #    if not create:
    #        # Simple build, do nothing.
    #        return
    #
    #    if extracted:
    #        try:
    #            for pmst in extracted:
    #                self.projectmilestones.add(pmst)
    #        except TypeError:
    #            self.projectmilestones.add(extracted)


class AssociatedFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssociatedFile

    current = True
    project = factory.SubFactory(Project)
    file_path = "some/fake/file.txt"
    # uploaded_by = "Bob"
    uploaded_by = factory.SubFactory(UserFactory)
    report_hash = "1234"


class SamplePointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SamplePoint

    project = factory.SubFactory(ProjectFactory)
    label = "123"
    # centroid of grid 2826
    geom = GEOSGeometry("POINT(-82.0416679344936 44.041664015521)")
