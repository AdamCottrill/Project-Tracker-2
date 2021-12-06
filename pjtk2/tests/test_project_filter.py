"""=============================================================
 c:/Users/COTTRILLAD/1work/Python/djcode/pjtk2/pjtk2/tests/test_project_filter.py
 Created: 24 Apr 2020 14:07:23

 DESCRIPTION:

  pjtk2.filters contains a django filters filter for projects that
  currently allows users to select subsets of project by:

  + year  (exact)
  + first_year (gte)
  + last_year (lte)
  + prj_cd__icontains
  + lake__abbrev (value in list)
  + protocol__abbrev (value in list)
  + project_type__id (value in list)
  + project_type__scope (value in list)

 A. Cottrill
=============================================================

"""
import pytest

from pjtk2.models import Project
from .factories import ProjectFactory, LakeFactory, ProjProtocolFactory, ProjTypeFactory
from pjtk2.filters import ProjectFilter


@pytest.fixture()
def projects(db):
    """create a simple project with basic approved and signoff milestones"""

    projtype1 = ProjTypeFactory(
        project_type="Recreataional Fishery Monitoring", scope="FD"
    )
    projtype2 = ProjTypeFactory(project_type="Independent Assessment", scope="FI")

    protocol1 = ProjProtocolFactory(
        protocol="Broad Scale Monitoring", abbrev="BSM", project_type=projtype1
    )
    protocol2 = ProjProtocolFactory(
        protocol="Roving Sport Creel", abbrev="RSC", project_type=projtype2
    )

    lake1 = LakeFactory(abbrev="SU", lake_name="Lake Superior")
    lake2 = LakeFactory(abbrev="HU", lake_name="Lake Huron")
    lake3 = LakeFactory(abbrev="ER", lake_name="Lake Erie")

    project1 = ProjectFactory.create(
        prj_cd="LSA_IA10_111",
        protocol=protocol1,
        lake=lake1,
        year=2010,
        project_type=projtype1,
    )

    project2 = ProjectFactory.create(
        prj_cd="LHA_SC14_111",
        protocol=protocol2,
        lake=lake2,
        year=2014,
        project_type=projtype2,
    )

    project3 = ProjectFactory.create(
        prj_cd="LEU_IA18_111",
        protocol=protocol1,
        lake=lake3,
        year=2018,
        project_type=projtype1,
    )

    return [project1, project2, project3]


@pytest.mark.django_db
def test_project_filter_year(projects):
    """if we pass a filter for a year, only projects run in that year
    should be included in the filtered queryset.
    """

    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"year": 2014}, queryset=queryset).qs

    assert filtered.count() == 1
    assert filtered[0].prj_cd == "LHA_SC14_111"


def test_project_filter_first_year(projects):
    """If we provide a filter for the first year, only projects run on
    or after that year should be include.
    """

    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"first_year": 2014}, queryset=queryset).qs

    assert filtered.count() == 2
    obs = {x.prj_cd for x in filtered}
    expected = {"LHA_SC14_111", "LEU_IA18_111"}
    assert obs == expected


def test_project_filter_last_year(projects):
    """If we provide a filter for the last year, only projects run on
    or before that year should be include.

    """

    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"last_year": 2014}, queryset=queryset).qs

    assert filtered.count() == 2
    obs = {x.prj_cd for x in filtered}
    expected = {"LSA_IA10_111", "LHA_SC14_111"}
    assert obs == expected


def test_project_filter_first_and_last_year(projects):
    """If we provide a filter for the first year and last year only
    projects run between those two years should be include.
    """
    queryset = Project.objects.all()
    filtered = ProjectFilter(
        data={"first_year": 2012, "last_year": 2016}, queryset=queryset
    ).qs

    assert filtered.count() == 1
    obs = {x.prj_cd for x in filtered}
    expected = {"LHA_SC14_111"}
    assert obs == expected


@pytest.mark.parametrize("partial", ["SC", "sc", "sC"])
def test_project_filter_prj_icontains(projects, partial):
    """The project filter acceps a partial project code. only projects
    that have that string in their project code should be returned.
    The filter must be case insensitive so that both 'LHA' and 'lha'
    will return the same result.
    """

    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"prj_cd__like": partial}, queryset=queryset).qs

    assert filtered.count() == 1
    obs = {x.prj_cd for x in filtered}
    expected = {"LHA_SC14_111"}
    assert obs == expected


pars = [("HU", {"LHA_SC14_111"}), ("HU,SU", {"LSA_IA10_111", "LHA_SC14_111"})]


@pytest.mark.parametrize("lake, expected", pars)
def test_project_filter_lake_abbrev(projects, lake, expected):
    """The project filter accepts a list of lake abbreviations - only
    projects run in those lakes that match the supplied abbreviation
    should be included in the filtered queryset.

    """
    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"lake": lake}, queryset=queryset).qs

    assert filtered.count() == len(expected)
    obs = {x.prj_cd for x in filtered}

    assert obs == expected


def test_project_filter_protocol_abbrev(projects):
    """The project filter accepts a list of protocol abbreviations -
    only projects that used protocols that match the supplied
    abbreviation should be included in the filtered queryset."""

    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"protocol": "BSM"}, queryset=queryset).qs

    assert filtered.count() == 2
    obs = {x.prj_cd for x in filtered}
    expected = {"LSA_IA10_111", "LEU_IA18_111"}
    assert obs == expected


def test_project_filter_project_type_id(projects):
    """The project filter accepts a list of project type id's - only
    projects that are of the specified type should be included in the
    filtered queryset."""

    my_project = Project.objects.get(prj_cd="LHA_SC14_111")
    project_type_id = str(my_project.project_type_id)

    queryset = Project.objects.all()
    filtered = ProjectFilter(
        data={"project_type": project_type_id}, queryset=queryset
    ).qs

    assert filtered.count() == 1
    obs = {x.prj_cd for x in filtered}
    expected = {"LHA_SC14_111"}
    assert obs == expected


def test_project_filter_project_type_scope(projects):
    """The project filter accepts a list of project scope
    abbreviations - only projects that are of that of of the specified
    scope should be included in the filtered queryset."""

    queryset = Project.objects.all()
    filtered = ProjectFilter(data={"scope": "FD"}, queryset=queryset).qs

    assert filtered.count() == 2
    obs = {x.prj_cd for x in filtered}
    expected = {"LSA_IA10_111", "LEU_IA18_111"}
    assert obs == expected
