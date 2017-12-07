from django.db.models.signals import pre_save
from django.conf import settings

import datetime
import pytz
import pytest

from .factories import ProjectFactory, ProjTypeFactory, MilestoneFactory

from pjtk2.models import ProjectMilestones, send_notice_prjms_changed
from pjtk2.templatetags.pjtk2_tags import fisheye_button


def get_project_link_url(label):
    """ pull out the detail url from the settings file.
    """

    url = settings.LOCAL_LINKS.get('project_types').get(label).get('detail_url')
    return url


def merge_data(project, milestone):
    """A little helper function to satisfy the data_merged milestone for
    this project.
    Arguments:
    - `project`:
    - `milestone`:

    """
    tmp = ProjectMilestones.objects.get(project=project,
                                        milestone=milestone)
    tmp.completed = datetime.datetime.now(pytz.utc)
    tmp.save()

    return None



@pytest.fixture(scope='function', autouse=True)
def disconnect_signals():
    '''disconnect the signals before each test - not needed here'''
    pre_save.disconnect(send_notice_prjms_changed,
                        sender=ProjectMilestones)


@pytest.mark.django_db
def test_fisheye_button_creel():
    """if we pass a creel project to our fisheye_button function, it
    should return a hyperlink to our creel project in the creel
    portal. The button should read View in 'Creel Portal'

    The test calls the fisheye_button function both before and after
    the data merge milestone has been satisfied.

    """

    ms =  MilestoneFactory.create(label='Data Merged')
    project_type_label = 'Creel Survey'
    url = get_project_link_url(project_type_label)
    project_type = ProjTypeFactory.create(project_type=project_type_label)
    project = ProjectFactory.create(project_type=project_type)

    #pre-data merge milestone
    button = fisheye_button(project)
    assert button is ""

    project.initialize_milestones()
    merge_data(project, ms)

    button = fisheye_button(project)
    assert "View in Creel Portal" in button
    assert url in button


@pytest.mark.django_db
def test_fisheye_button_stocking():
    """if we pass a fish stocking project to our fisheye_button function,
    it should return a hyperlink to fsis-II for the same year as our
    project. The button should read View in 'FSIS-II'

    The test calls the fisheye_button function both before and after
    the data merge milestone has been satisfied.

    """
    ms =  MilestoneFactory.create(label='Data Merged')
    project_type_label = 'Fish Stocking'
    url = get_project_link_url(project_type_label)
    project_type = ProjTypeFactory.create(project_type=project_type_label)
    project = ProjectFactory.create(project_type=project_type)

    #pre-data merge milestone
    button = fisheye_button(project)
    assert button is ""

    project.initialize_milestones()
    merge_data(project, ms)

    button = fisheye_button(project)
    assert "View in FSIS-II" in button
    assert url in button


@pytest.mark.django_db
def test_fisheye_button_offshore():
    """if we pass an offshore index project to our fisheye_button
    function, it should return a hyperlink to the detail page for that
    project in fisheye. The button should read 'View in Fisheye'

    The test calls the fisheye_button function both before and after
    the data merge milestone has been satisfied.

    """

    ms =  MilestoneFactory.create(label='Data Merged')
    project_type_label = 'Offshore Index Netting'
    url = get_project_link_url(project_type_label)
    project_type = ProjTypeFactory.create(project_type=project_type_label)
    project = ProjectFactory.create(project_type=project_type)

    #pre-data merge milestone
    button = fisheye_button(project)
    assert button is ""

    project.initialize_milestones()
    merge_data(project, ms)

    button = fisheye_button(project)
    assert "View in Fisheye" in button
    assert url in button


@pytest.mark.django_db
def test_fisheye_button_nearshore():
    """if we pass an offshore index project to our fisheye_button
    function, it should return a hyperlink to the detail page for that
    project in fisheye. The button should read 'View in Fisheye'

    The test calls the fisheye_button function both before and after
    the data merge milestone has been satisfied.

    """

    ms =  MilestoneFactory.create(label='Data Merged')
    project_type_label = 'Nearshore Index Netting'
    url = get_project_link_url(project_type_label)
    project_type = ProjTypeFactory.create(project_type=project_type_label)
    project = ProjectFactory.create(project_type=project_type)

    #pre-data merge milestone
    button = fisheye_button(project)
    assert button is ""

    project.initialize_milestones()
    merge_data(project, ms)

    #post data-merge milestone
    button = fisheye_button(project)
    assert "View in Fisheye" in button
    assert url in button


@pytest.mark.django_db
def test_fisheye_button_synthesis():
    """if we pass an a syntheis type project (or any project that does not
    have a corresponding application) to our fisheye_button function,
    it should return an empty string.

    The test calls the fisheye_button function both before and after
    the data merge milestone has been satisfied.

    """

    ms =  MilestoneFactory.create(label='Data Merged')
    project_type_label = 'Synthesis and Analysis'
    project_type = ProjTypeFactory.create(project_type=project_type_label)
    project = ProjectFactory.create(project_type=project_type)

    button = fisheye_button(project)
    assert button is ""
