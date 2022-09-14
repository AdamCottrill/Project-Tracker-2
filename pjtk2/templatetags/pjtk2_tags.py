from django import template
from django.conf import settings
from pjtk2.models import Project, Bookmark, ProjectType, Milestone

from django.template.defaultfilters import stringfilter


# from django.contrib.auth import user
from django.utils.safestring import mark_safe

register = template.Library()


def do_if_Bookmarked(parser, token):
    """modified from PracticalDjangoProjects (page 193)"""
    bits = token.contents.split()
    if len(bits) != 3:
        raise template.TemplateSyntaxError("%s tag takes two arguments" % bits[0])
    nodelist_true = parser.parse(("else", "endif_bookmarked"))
    token = parser.next_token()
    if token.contents == "else":
        nodelist_false = parser.parse(("endif_bookmarked",))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()

    return IfBookmarkedNode(bits[1], bits[2], nodelist_true, nodelist_false)


class IfBookmarkedNode(template.Node):
    def __init__(self, user, project, nodelist_true, nodelist_false):
        self.nodelist_false = nodelist_false
        self.nodelist_true = nodelist_true
        self.user = template.Variable(user)
        self.project = template.Variable(project)

    def render(self, context):
        try:
            user = self.user.resolve(context)
            project = self.project.resolve(context)
        except template.VariableDoesNotExist:
            return ""
        if Bookmark.objects.filter(user__pk=user.id, project__slug=project.slug):
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)


register = template.Library()
register.tag("if_bookmarked", do_if_Bookmarked)


@register.filter
def milestone_status_glyph(status):
    """ """

    default = '<span class="fa fa-minus" aria-label="Not required and not done"></span>'

    glyphs = {
        "required-done": '<span class="fa fa-check" aria-label="Required and done" style="color:green"></span>',
        "required-notDone": '<span class="fa fa-question" aria-label="Required and not done" style="color:red"></span>',
        "notRequired-done": '<span class="fa fa-check" aria-label="Not required and done"></span>',
        "notRequired-notDone": default,
    }

    return mark_safe(glyphs.get(status, default))


@register.filter
def highlight_status(status):
    """a little filter to colour our status entires in project lists."""

    status_colours = {"Cancelled": "red", "Ongoing": "blue", "Complete": "green"}

    return status_colours.get(status, "black")


@register.filter
def fisheye_button(project):
    """a template filter to return a bootstrap styled button link to the
    project detail page in fisheye, fsis-ii or the creel portal.
    Controlled by the values in LOCAL_LINKS in settings/base.py

    The LOCAL_LINKS contains the base ip address were the other apps
    are being hosted, followed by a series of dictionaries - one for
    each proejct type.  The project dictionaries contain these elements:

    - port : the port the application is listening on

    - detail_url : the url that contain the detail view we want to access

    - button_label: the label that will appear on the rendered button

    - identifier: the name of the field that when combined with detail
      url, returns the appropriate detail view.  Usually this is
      'slug', but inthe case of fish stocking is 'year'

    - if local links can't be found or the project type is not in the
      list of projects included in local links, the function retuns an
      empty string.

    """
    local_links = settings.LOCAL_LINKS
    if local_links is None:
        return ""
    else:
        merged = Milestone.objects.filter(label="Data Merged").first()
        if merged is None:
            return ""
        else:
            project_type = project.project_type.project_type
            project_vals = local_links.get("project_types").get(project_type)

            if project_vals and project.milestone_complete(merged):
                project_vals["ipaddress"] = local_links.get("ipaddress")
                project_vals["id_val"] = getattr(
                    project, project_vals.get("identifier")
                )
                url = "http://{ipaddress}:{port}/{detail_url}/{id_val}".format(
                    **project_vals
                )
                link = '<a class="btn btn-primary" href="{}" role="button">{}</a>'
                link = link.format(url, project_vals["button_label"])
                return mark_safe(link)
            else:
                return ""


@register.filter(name="addcss")
def addcss(field, css):
    """from http://vanderwijk.info/blog/adding-css-classes-formfields-in-django-templates/"""
    return field.as_widget(attrs={"class": css})


@register.simple_tag(takes_context=True)
def query_transform(context, include_page=False, **kwargs):
    """
    Returns the URL-encoded querystring for the current page,
    updating the params with the key/value pairs passed to the tag.

    E.g: given the querystring ?foo=1&bar=2
    {% query_transform bar=3 %} outputs ?foo=1&bar=3
    {% query_transform foo='baz' %} outputs ?foo=baz&bar=2
    {% query_transform foo='one' bar='two' baz=99 %}
    outputs ?foo=one&bar=two&baz=99

    A RequestContext is required for access to the current querystring.

    from: https://gist.github.com/benbacardi/d6cd0fb8c85e1547c3c60f95f5b2d5e1

    if page is true, we will return the page number tag too, if it is
    false, we want to strip it out and reset our filters to page 1.
    This allows the same template tag to be used in paginators and
    'refinement' widgets.  Without, refinement widgets may point to a
    page that doesn't exist after the new filter has been applied.

    """

    query = context["request"].GET.copy()
    for k, v in kwargs.items():
        query[k] = v

    if query.get("page") and not include_page:
        query.pop("page")
    return query.urlencode()


@register.simple_tag(takes_context=True)
def strip_parameter(context, param):
    """
    A template tag to remove the specified parameter from the url
    string.  If there are no parameter left, it returns the bare
    url (without any parameters or ?-mark)
    """

    query = context["request"].GET.copy()
    query.pop(param, None)

    if len(query):
        return "?" + query.urlencode()
    else:
        return context["request"].path


@register.filter
@stringfilter
def space(string):
    """A simple little template filter to replace underscores with spaces"""
    return mark_safe(string.replace("_", " "))


@register.filter
@stringfilter
def classify(project_attribute):
    """Given a project attribute, return a string representation that could
    be used to to assign a class in an html template.

    """

    classString = project_attribute.replace(" ", "-").replace("_", "-").lower()

    return mark_safe(classString)
