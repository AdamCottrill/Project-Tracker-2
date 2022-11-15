
#this code has not been tests, but should be very close:

import pytest
from django.urls import reverse
from pytest_django.asserts import assertContains, assertTemplateUsed

from .factories import ProjectImageFactory
from .pytest_fixtures import project, user


@pytest.mark.django_db
def test_project_image_alt_text_project_detail_page(client, user, project):
    """A sentence or two describing what this test is looking for and
    what it means if it fails.

    """
    caption = "Image Caption Test"
    alt_text = "Image Alt Text Test"
    ProjectImageFactory(project=project, caption=caption, alt_text=alt_text)  # alt_text=alt_text

    url = reverse("project_detail", kwargs={"slug": project.slug})
    response = client.get(url)
    assert response.status_code == 200
    assertTemplateUsed(response, "pjtk2/projectdetail.html")

    # expected = "what ever string you speficed as alt_text for the ProjectImage."
    # or maybe even better because it includes the alt_text attribute:
    expected = 'alt_text="Image Alt Text Test"'
    assertContains(response, caption)
    assertContains(response, alt_text)