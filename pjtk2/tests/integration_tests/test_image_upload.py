"""This file tests that the views associated with image uploads
function as expected.  Views to test include:

- project_add_image

  - login is required on this view

  - a form that is used to submit images - will need tests for both
   get and post requests and good and bad data.

  - if the project does not exists - we should raise a 404

- edit-image

  - login is required on this view

  - a view to edit the image attributes - caption and whether or not
    it should be included in the annual report.  THere should never be
    any more than two 'report' images associated with a project.  -
    this view processes a form, so we will need both get and post
    requests, as well as good and bad data.

  - if the project does not exists - we should raise a 404

- project_images

  - login is required on this view

  - a view to list the images associated with a project.  It should
    return the images in the order of the 'order' field

  - if the project does not exists - we should raise a 404

- project_sort_images

  - login is required on this view

  - this view is a little different in that it does not return a
    response.  It is called from ajax emitted by project images view.
    We should be able to create some images in a known order, submit a
    request to this view with a different order and confirm that the
    image order has been changed.

- delete_image_file

  - login is required on this view

  - a view to remove files associated with a project. If this is a GET
    request, redirect to a confirmation page.  If it is a POST, delete
    the associated image and return to the project detail page.

  - if the project does not exists - we should raise a 404

"""


import pytest

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from pjtk2.models import ProjectImage
from pjtk2.tests.factories import ProjectImageFactory
from pjtk2.tests.pytest_fixtures import user, joe_user, manager, project, dba


# a small binary image file we will use in these tests:
SMALL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04"
    b"\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
    b"\x02\x4c\x01\x00\x3b"
)


@pytest.mark.django_db
def test_image_urls_redirect_to_login(client, project, user):
    """All of the views assocaited with a project require users to be logged
    in.  If the view is accessed by a user who is not logged in, they
    will be re-directed to the login page.
    """

    image = ProjectImageFactory(project=project)

    urls = [
        ["project_add_image", {"slug": project.slug}],
        ["project_images", {"slug": project.slug}],
        ["project_sort_images", {"slug": project.slug}],
        ["project_edit_image", {"pk": image.id}],
        ["delete_image_file", {"pk": image.id}],
    ]

    for url_name, kwargs in urls:
        response = client.get(reverse(url_name, kwargs=kwargs), follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Project Tracker Login" in content
        assert "registration/login.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_image_urls_joe_user_redirect_to_details(client, project, joe_user):
    """Only users who can edit a project can access the urls, someone who
    cannot edit the project should be red-rected to the project detail
    page.

    The project lead is user, so joe_user should not be able to edit it.

    """

    image = ProjectImageFactory(project=project)

    urls = [
        ["project_add_image", {"slug": project.slug}],
        ["project_images", {"slug": project.slug}],
        # ['project_sort_images',{'slug':project.slug}],
        ["project_edit_image", {"pk": image.id}],
        ["delete_image_file", {"pk": image.id}],
    ]

    for url_name, kwargs in urls:
        login = client.login(username=joe_user.username, password="Abcd1234")
        assert login is True
        response = client.get(reverse(url_name, kwargs=kwargs), follow=True)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "<h2>{}</h2>".format(project.prj_nm) in content

        assert "pjtk2/projectdetail.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_nonexistant_image_redirect_to_404(client, project, user):
    """If we try to access any of our image urls with non-existant project
    slug or image id, a 404 will be raised.  the user who is logged in
    is the project lead so he should be able to edit the project or
    images if they actually existed.
    """

    image = ProjectImageFactory(project=project)

    urls = [
        ["project_add_image", {"slug": "zzz_zz99_zzz"}],
        ["project_images", {"slug": "zzz_zz99_zzz"}],
        # ['project_sort_images',{'slug':project.slug}],
        ["project_edit_image", {"pk": 999999}],
        ["delete_image_file", {"pk": 999999}],
    ]

    for url_name, kwargs in urls:
        login = client.login(username=user.username, password="Abcd1234")
        assert login is True
        response = client.get(reverse(url_name, kwargs=kwargs), follow=True)
        assert response.status_code == 404
        assert "404.html" in [t.name for t in response.templates]


@pytest.mark.django_db
def test_add_image_get_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to add an image (i.e. - they should be
    able to view the tempalte form with a GET request.)
    """

    users = [user, manager, dba]

    for current_user in users:

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True
        response = client.get(
            reverse("project_add_image", kwargs={"slug": project.slug})
        )

        assert response.status_code == 200
        template = "pjtk2/project_image_upload.html"
        assert template in [t.name for t in response.templates]

        content = response.content.decode("utf-8")
        shouldbe = "<h4>Add an image or graph for {}</h4>".format(project.prj_nm)

        assert shouldbe in content

        # make sure that our users are actually changing.
        assert current_user.first_name in content


@pytest.mark.django_db
def test_add_image_post_save_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to add an image (i.e. - when they submit
    a POST request with the data necessary to create an image, it
    should be associated with the project.)

    If save is included in the POST data - the response should
    redirect back to the detail page four our project.

    """

    users = [user, manager, dba]

    for i, current_user in enumerate(users):

        img = SimpleUploadedFile(
            "myimage{}.jpg".format(i), SMALL_GIF, content_type="image/gif"
        )

        image_data = {
            "order": i,
            "caption": "image number {}".format(i),
            "alt_text": "image alt text",
            "project": project.id,
            "report": False,
            "image_path": img,
            "save": True,
        }

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True

        url = reverse("project_add_image", kwargs={"slug": project.slug})
        response = client.post(path=url, data=image_data, follow=True)
        assert response.status_code == 200
        assert "pjtk2/projectdetail.html" in [t.name for t in response.templates]
        content = response.content.decode("utf-8")
        assert "<h2>{}</h2>".format(project.prj_nm) in content

        print("i={}".format(i))
        print("project.images.all()={}".format(project.images.all()))

        assert len(project.images.all()) == i + 1


@pytest.mark.django_db
def test_add_image_post_add_more_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to add an image (i.e. - when they submit
    a POST request with the data necessary to create an image, it
    should be associated with the project)

    If 'save' is included in the POST data - the response should
    return to the form.

    """

    users = [user, manager, dba]

    for i, current_user in enumerate(users):

        img = SimpleUploadedFile(
            "myimage{}.jpg".format(i), SMALL_GIF, content_type="image/gif"
        )

        # NO 'save' -
        image_data = {
            "order": i,
            "caption": "image number {}".format(i),
            "alt_text": "image alt text",
            "project": project.id,
            "report": False,
            "image_path": img,
        }

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True

        url = reverse("project_add_image", kwargs={"slug": project.slug})
        response = client.post(path=url, data=image_data, follow=True)
        assert response.status_code == 200

        template = "pjtk2/project_image_upload.html"
        assert template in [t.name for t in response.templates]

        content = response.content.decode("utf-8")
        shouldbe = "<h4>Add an image or graph for {}</h4>".format(project.prj_nm)
        assert shouldbe in content

        # make sure that our users are actually changing.
        assert current_user.first_name in content

        assert len(project.images.all()) == i + 1


@pytest.mark.django_db
def test_edit_image_get_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to edit the attributes of an image
    (i.e. - they should be able to view the tempalte form with a
    simple GET request).

    """

    image = ProjectImageFactory(project=project)

    users = [user, manager, dba]

    for current_user in users:

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True
        response = client.get(reverse("project_edit_image", kwargs={"pk": image.id}))

        assert response.status_code == 200
        template = "pjtk2/edit_image.html"
        assert template in [t.name for t in response.templates]

        content = response.content.decode("utf-8")
        shouldbe = "<h4>{}</h4>".format(project.prj_nm)
        assert shouldbe in content
        shouldbe = "Should this image be included in the annual report"
        assert shouldbe in content
        # make sure that our users are actually changing.
        assert current_user.first_name in content


@pytest.mark.django_db
def test_edit_image_post_next_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to edit the attributes of an image
    (i.e. - they should be able to alter the appributes of an image
    with a post request request)

    If a valid 'next' parmeter is provided - the reponse should go to it.

    """
    image = ProjectImageFactory(project=project, caption="image caption", report=False)

    users = [user, manager, dba]

    for i, current_user in enumerate(users):

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True

        next_url = reverse("project_images", kwargs={"slug": project.slug})

        new_caption = "new caption {}".format(i)
        image_data = {"caption": new_caption, "alt_text": "image alt text" ,"next": next_url}

        url = reverse("project_edit_image", kwargs={"pk": image.id})

        response = client.post(url, data=image_data, follow=True)

        # verify that we have gone to our next url
        # In this case - the image sorter:
        assert response.status_code == 200
        assert "pjtk2/project_sort_images.html" in [t.name for t in response.templates]
        content = response.content.decode("utf-8")
        assert "<h2>Images for {}</h2>".format(project.prj_nm) in content
        assert "Drag to re-order the images. Double click to edit." in content

        # verify that the caption has changed
        image = ProjectImage.objects.get(id=image.id)
        assert image.caption == new_caption


@pytest.mark.django_db
def test_edit_image_post_no_next_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to edit the attributes of an image
    (i.e. - they should be able to alter the appributes of an image
    with a post request request)

    If there is NO 'next' parmeter provided in the post data, the
    response should resolve to the detail page for the project.

    """

    image = ProjectImageFactory(project=project, caption="image caption", alt_text="image alt text", report=False)

    users = [user, manager, dba]

    for i, current_user in enumerate(users):

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True

        new_caption = "new caption {}".format(i)
        # no 'next'
        image_data = {"caption": new_caption, "alt_text": "image alt text"}

        url = reverse("project_edit_image", kwargs={"pk": image.id})

        response = client.post(url, data=image_data, follow=True)

        assert response.status_code == 200
        assert "pjtk2/projectdetail.html" in [t.name for t in response.templates]

        content = response.content.decode("utf-8")
        assert "<h2>{}</h2>".format(project.prj_nm) in content
        # verify that the caption has changed
        image = ProjectImage.objects.get(id=image.id)
        assert image.caption == new_caption


@pytest.mark.django_db
def test_edit_image_max_report_cutoff(client, project, user):
    """THere is logic in the view that ensure that a maximim number of
    images can be included in the report - this test ensures that the
    maxium number never exceeds that threshhold.

    For now MAX


    """

    max_images = settings.MAX_REPORT_IMG_COUNT

    # create one more image than we can report on:
    for img in range(max_images + 1):
        caption = "Fake Image {}".format(img)
        ProjectImageFactory(project=project, order=img, caption=caption, report=True)

    report_images = len(ProjectImage.objects.filter(report=True))
    assert report_images > max_images

    # now if we edit one of our images, the number of report images
    # will be same as max_images

    image = project.images.first()
    login = client.login(username=user.username, password="Abcd1234")
    assert login is True

    image_data = {"caption": "new caption", "alt_text":"new alt text", "report": True}

    url = reverse("project_edit_image", kwargs={"pk": image.id})

    response = client.post(url, data=image_data, follow=True)

    assert response.status_code == 200

    report_images = len(ProjectImage.objects.filter(report=True))
    assert report_images == max_images


@pytest.mark.django_db
def test_delete_image_get_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to delete an image.  The GET request should just
    show a confrimation page.
    """

    image = ProjectImageFactory(project=project)

    assert len(project.images.all()) == 1

    users = [user, manager, dba]

    for current_user in users:

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True
        response = client.get(reverse("delete_image_file", kwargs={"pk": image.id}))

        assert response.status_code == 200
        template = "pjtk2/confirm_image_delete.html"
        assert template in [t.name for t in response.templates]

        content = response.content.decode("utf-8")
        shouldbe = "<h3>Project: {}".format(project.prj_nm)
        assert shouldbe in content

        shouldbe = "Are you sure you want to permanently delete this image"
        assert shouldbe in content
        # make sure that our users are actually changing.
        assert current_user.first_name in content

        assert len(project.images.all()) == 1


@pytest.mark.django_db
def test_delete_image_post_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to delete an image.  The POST request delete the
    ProjectImage instance.
    """

    # our project should not have any images before we start
    assert len(project.images.all()) == 0

    users = [user, manager, dba]

    for current_user in users:

        image = ProjectImageFactory(project=project)
        assert len(project.images.all()) == 1

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True
        response = client.post(
            reverse("delete_image_file", kwargs={"pk": image.id}), follow=True
        )

        # we shouldbe back on our project details page.
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "<h2>{}</h2>".format(project.prj_nm) in content
        assert "pjtk2/projectdetail.html" in [t.name for t in response.templates]

        # our project should not have any images associated with it again
        assert len(project.images.all()) == 0


@pytest.mark.django_db
def test_list_project_image_canedit(client, project, user, manager, dba):
    """Verify that users who can edit the project - the project lead, the
    dba and manager are able to see the sortable image list. Actual
    sorting is done using ajax and JQuery - not tested here.

    """

    # some images:
    captions = ["The first image", "The second image", "The third image"]

    for i, caption in enumerate(captions):
        ProjectImageFactory(project=project, order=i, caption=caption)

    users = [user, manager, dba]

    for current_user in users:

        login = client.login(username=current_user.username, password="Abcd1234")
        assert login is True
        response = client.post(
            reverse("project_images", kwargs={"slug": project.slug}), follow=True
        )

        # we shouldbe back on our project details page.
        assert response.status_code == 200
        assert "pjtk2/project_sort_images.html" in [t.name for t in response.templates]

        content = response.content.decode("utf-8")
        assert "<h2>Images for {}</h2>".format(project.prj_nm) in content
        assert "Drag to re-order the images. Double click to edit." in content

        captions = ["The first image", "The second image", "The third image"]
        for caption in captions:
            assert caption in content
