"""=============================================================
 c:/Users/COTTRILLAD/1work/Python/djcode/apps/pjtk2/pjtk2/tests/integration_tests/test_project_form.py
 Created: 23 Jul 2020 10:57:39

 DESCRIPTION:

  + project owner should not be rendered for regular employees

  + when a project is submitted and project owner is null, it should
    be the requested user

  + users:

  + when a project is submitted and project owner is already populated
  but not visible, it should be unchanged (users cannot change project
  owners)

  + managers and dbas:
  + when

 A. Cottrill
=============================================================

"""

import pytest

from django.urls import reverse

# from pjtk2.models import Project
from pjtk2.tests.factories import (
    UserFactory,
    EmployeeFactory,
    ProjectFactory,
    MilestoneFactory,
)

# from pjtk2.tests.pytest_fixtures import user, joe_user, manager, project, dba
from pjtk2.tests.pytest_fixtures import manager


@pytest.fixture()
def employee(db, manager):
    """return a normal employee named homer"""
    password = "Abcd1234"
    myuser = UserFactory(
        username="hsimpson", first_name="Homer", last_name="Simpson", password=password
    )
    EmployeeFactory(user=myuser, role="employee")
    return myuser


@pytest.fixture()
def dba(db):
    """return a normal employee named homer"""
    password = "Abcd1234"
    myuser = UserFactory(
        username="bgumble", first_name="Barney", last_name="Gumble", password=password
    )
    EmployeeFactory(user=myuser, role="dba")
    return myuser


@pytest.fixture()
def project(employee):
    MilestoneFactory(label="Approved")
    MilestoneFactory(label="Sign Off")

    project = ProjectFactory(prj_cd="LHA_IA12_111", owner=employee)
    return project


# ===========================================================
#      NEW PROJECT - PROJECT OWNER WIDGET VISIBILITY


@pytest.mark.django_db
def test_owner_widget_visibility_new_project_employee(client, employee):
    """When an employee creates a new project, and they are not a manager,
    admin, or dba, the project own widget should be disabled.
    """

    login = client.login(username=employee.username, password="Abcd1234")
    assert login is True

    response = client.get(reverse("NewProject"), follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = (
        '<select name="owner" class="form-control " disabled="disabled" '
        + 'id="id_owner">'
    )
    assert html in content


@pytest.mark.django_db
def test_owner_widget_visibility_new_project_dba(client, dba):
    """When an employee creates a new project, and they are a dba,
    they should see the project owner widget and it should not be disabled.
    """

    login = client.login(username=dba.username, password="Abcd1234")
    assert login is True

    response = client.get(reverse("NewProject"), follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = '<select name="owner" class="form-control " required id="id_owner">'
    assert html in content


@pytest.mark.django_db
def test_owner_widget_visibility_new_project_manager(client, manager):
    """When an employee creates a new project, and they are a manager,
    they should see the project owner widget.
    """

    login = client.login(username=manager.username, password="Abcd1234")
    assert login is True

    response = client.get(reverse("NewProject"), follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = '<select name="owner" class="form-control " required id="id_owner">'
    assert html in content


# ===========================================================
#      COPY PROJECT - PROJECT OWNER WIDGET VISIBILITY


@pytest.mark.django_db
def test_owner_widget_visibility_copied_project_user(client, employee, project):
    """When an employee creates a new project by copying an existing
    project, and they are not a manager, admin, or dba, they should
    *NOT* see the project owner widget.

    """

    login = client.login(username=employee.username, password="Abcd1234")
    assert login is True
    url = reverse("CopyProject", args=(project.slug,))
    response = client.get(url, follow=True)

    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = (
        '<select name="owner" class="form-control " disabled="disabled" '
        + 'id="id_owner">'
    )
    assert html in content


@pytest.mark.django_db
def test_owner_widget_visibility_copied_project_dba(client, dba, project):
    """When an employee creates a new project by copying and existing project, and they are a dba,
    they should see the project owner widget.
    """

    login = client.login(username=dba.username, password="Abcd1234")
    assert login is True

    url = reverse("CopyProject", args=(project.slug,))
    response = client.get(url, follow=True)

    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = '<select name="owner" class="form-control " required id="id_owner">'
    assert html in content


@pytest.mark.django_db
def test_owner_widget_visibility_copied_project_manager(client, manager, project):
    """When an employee creates a project by copying and existing project,
    and they are a manager, they should see the project owner widget.

    """

    login = client.login(username=manager.username, password="Abcd1234")
    assert login is True

    url = reverse("CopyProject", args=(project.slug,))
    response = client.get(url, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = '<select name="owner" class="form-control " required id="id_owner">'
    assert html in content


# ===========================================================
#      EDIT PROJECT - PROJECT OWNER WIDGET VISIBILITY


@pytest.mark.django_db
def test_owner_widget_visibility_edit_project_user(client, employee, project):
    """When an employee editing an existing
    project, and they are not a manager, admin, or dba, they should
    *NOT* see the project owner widget.

    """

    login = client.login(username=employee.username, password="Abcd1234")
    assert login is True
    url = reverse("EditProject", args=(project.slug,))
    response = client.get(url, follow=True)

    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = (
        '<select name="owner" class="form-control " disabled="disabled" '
        + 'id="id_owner">'
    )
    assert html in content


@pytest.mark.django_db
def test_owner_widget_visibility_edit_project_dba(client, dba, project):
    """When a dba edits and existing project they should see the project owner widget."""

    login = client.login(username=dba.username, password="Abcd1234")
    assert login is True

    url = reverse("EditProject", args=(project.slug,))
    response = client.get(url, follow=True)

    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = '<select name="owner" class="form-control " required id="id_owner">'
    assert html in content


@pytest.mark.django_db
def test_owner_widget_visibility_edit_project_manager(client, manager, project):
    """When a manager edits an existing project they should see the
    project owner widget.

    """

    login = client.login(username=manager.username, password="Abcd1234")
    assert login is True

    url = reverse("EditProject", args=(project.slug,))
    response = client.get(url, follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = '<select name="owner" class="form-control " required id="id_owner">'
    assert html in content


@pytest.mark.adoa
@pytest.mark.django_db
def test_tags_aria_label(client, employee):
    """
    The project detail form has a TagField that need to have a
    aria-label. It's value should be set to keywords.
    """

    login = client.login(username=employee.username, password="Abcd1234")
    assert login is True

    response = client.get(reverse("NewProject"), follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    html = 'aria-label="keywords"'

    assert html in content


elements = [
    '<label class="sr-only" for="id_funding_sources-0-DELETE">Delete</label>',
    'aria-label="project-abstract"',
    'aria-label="project-comments-remarks"',
    'aria-label="project-risks"',
]


@pytest.mark.adoa
@pytest.mark.django_db
@pytest.mark.parametrize("element", elements)
def test_aria_labels(client, employee, element):
    """The project detail form has a number of aria-labels that were
    missing from the orignal tempate, and are required to meet adoa
    compliance.  THis test verifies that they are rendered in the html
    repsonse.

    """

    login = client.login(username=employee.username, password="Abcd1234")
    assert login is True

    response = client.get(reverse("NewProject"), follow=True)
    assert response.status_code == 200
    content = response.content.decode("utf-8")

    assert element in content
