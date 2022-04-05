import csv
import os

import django_settings
from pjtk2.models import ProjectProtocol, ProjectType

HERE = "c:/Users/COTTRILLAD/1work/Python/djcode/pjtk2/pjtk2/utils"

# project types:

ptypes = []
fname = os.path.join(HERE, "project_types_march2020.csv")
with open(fname, newline="") as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        ptypes.append(row)


protocols = []
fname = os.path.join(HERE, "protocols_march_2020.csv")
with open(fname, newline="") as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        protocols.append(row)


# now create oru new objects and add them to the database

scope_lookup = {
    "Fishery Dependent": "FD",
    "Fishery Independent": "FI",
    "Multiple Sources": "MS",
}

items = []
for item in ptypes:
    x = ProjectType(
        scope=scope_lookup[item[0]], project_type=item[1], field_component=bool(item[2])
    )
    items.append(x)
# clear out the old
ProjectType.bulk_create(items)

project_types = {x.project_type: x for x in ProjectType.objects.all()}

items = []
for item in protocols:
    x = Protocol(
        project_type=project_types.get(item[0]), protocol_label=item[1], abbrev=item[2]
    )
    items.append(x)

Protocols.bulk_create(items)

# ===============================================
#       PROJECT IMAGES

# we need to get all of the image files and their captions from the
# annual report directory:

src_dir = (
    "C:/Users/COTTRILLAD/1work/ProjectMgt/Annual_Project_Report/figures/huronfigures"
)
figure_catalog = os.path.join(src_dir, "figure_catalog.csv")

trg_dir = "C:/Users/COTTRILLAD/1work/Python/djcode/pjtk2/uploads/project_images"


# get a prj_cd_cache to minimize queries
# prj_cd_catche = {x.prj_cd: x  for x in Project.objects.all()}

# read in the figure cataloge
figures = []
with open(figure_catalog, newline="") as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        figures.append(row)


# for each figure in the figure cataloge, create a directory in the
# target directory if it does not exist and copy the file from the src
# dirctory to trg directory, and create a project image object using the caption from the cataloge.
# the image path that needs to be saved with the image will be of the form:
# project_images/{prj_cd}/{file_name}


# ===============================================
#    PROJECT SAMPLE POINTS

# the sample points are very similar to the project images read in the
# points (either in spreadsheet or csv format), lookup the project
# code, create the geos Point object, and create the sample points.

from django.contrib.gis.geos import GEOSGeometry

src_file = (
    "C:/Users/COTTRILLAD/1work/ProjectMgt/Annual_Project_Report/"
    + "2016_Sample_points.csv"
)
pts = []
with open(src_file, newline="") as csvfile:
    csvreader = csv.reader(csvfile)
    for row in csvreader:
        project = project_cache.get(pt[0])
        label = pt[1]
        wkt = "POINT({} {})".format(pt[3], pt[2])
        geopt = GEOSGeometry(wkt, srid=4326)
        pts.append(SamplePoint(project=project, label=label, geom=geopt))

SamplePoint.objects.bulk_create(pts)

# don't forget to:
#  - update the spatial data from Grandwazoo
#  - update the convex hull for each project
# resave each point to populate the pop-up text


# =========================================
#     LAKE SUPERIOR IMAGE DIRECORIES

xlsx_file = (
    "C:/Users/COTTRILLAD/1work/ProjectMgt/Annual_Project_Report/"
    + "figures/superiorfigures/figure_catalog.xlsx"
)
wb = openpyxl.load_workbook(xlsx_file)
ws = wb.get_sheet_by_name("figure_catalog")
image_attrs = []

for row in ws.iter_rows():
    image_attrs.append(
        {"prj_cd": row[0].value, "fname": row[1].value, "caption": row[2].value}
    )
# remove the column heading
image_attrs.pop(0)

# lets make sure tha all of our project codes are real projects:


pc = set([x["prj_cd"] for x in image_attrs])
for x in pc:
    if project_cache.get(x) is None:
        print(x)

# now - loop over our image attributes and verify the project directory exists

IMG_SRC_DIR = (
    "C:/Users/COTTRILLAD/1work/ProjectMgt/Annual_Project_Report/figures/superiorfigures"
)

for x in pc:
    img_dir = os.path.join(IMG_SRC_DIR, x)
    if os.path.isdir(img_dir) is False:
        print("Can't find directory for ({})".format(x))


# now loop over the files in the spreadsheets and see how many don't exists:
# If a file cannot be found, report the files that were found:
# looking for:
# >
# >


for img in image_attrs:
    prj_cd = img.get("prj_cd")
    fname = img.get("fname")
    if fname.endswith("pdf") or fname.endswith("docx"):
        print("{}/{}?".format(prj_cd, fname))
    img_path = os.path.join(IMG_SRC_DIR, prj_cd, fname)
    if os.path.exists(img_path) is False:
        print("\nUnable to find:\n{}/{}".format(prj_cd, fname))
        found = os.listdir(os.path.split(img_path)[0])
        if found:
            print("found:")
            [print("{}/{}".format(prj_cd, x)) for x in found]


# to update the project types and project protocols, we are going to
# need a couple of caches:
protocol_cache = {x.abbrev: x for x in ProjectProtocol.objects.all()}

project_cache = {x.prj_cd: x for x in Project.all_objects.all()}

projecttype_cache = {x.project_type: x for x in ProjectType.objects.all()}


projects = Project.objects.filter(prj_cd__contains="_CH")
protocol = protocol_cache["DCR"]

for project in projects:
    project.protocol = protocol
    project.project_type = protocol.project_type
    project.save()


# fish Stocking - all rehab for now.
projects = Project.objects.filter(prj_cd__contains="_FS")
protocol = protocol_cache["FSR"]

for project in projects:
    project.protocol = protocol
    project.project_type = protocol.project_type
    project.save()


# Catch Sampling - all onboard for now


def update_projtypes_and_protocols(ptype, protocol):
    projects = Project.objects.filter(prj_cd__contains=ptype).filter(
        project_type__isnull=True
    )
    print("found {} {} projects.".format(len(projects), ptype))
    protocol = protocol_cache[protocol]

    for project in projects:
        project.protocol = protocol
        project.project_type = protocol.project_type
        project.save()


update_projtypes_and_protocols("_CF", "CFO")
update_projtypes_and_protocols("_XX", "CFO")
update_projtypes_and_protocols("_CD", "CFO")

# contamiant collections
update_projtypes_and_protocols("_CC", "CC")


# Sport Creels - roving for now
update_projtypes_and_protocols("_SC", "SCR")


# Fishways
update_projtypes_and_protocols("_IM", "FMA")


# Telemetry
update_projtypes_and_protocols("_TE", "TE")

# CWT Recoveries
update_projtypes_and_protocols("_CWT", "CWT")

update_projtypes_and_protocols("_TR", "TR")


# Lamprey monitoring and recovery
update_projtypes_and_protocols("_LAM", "IJC")


# AR - Assessment Reporting
# BN - Benthic Sampling
# SD - Angler Diary Programs
# SS - status of stocks
# HA - Hydroaccoustic Assessment


# nearshore proejcts with UNKN PROTOCOL:

# PRJ_CD	protocol
# LHA_IA08_260	UNKN
# LHA_IA09_260	UNKN
# LHA_IA09_261	UNKN
# LHA_IS93_013	UNKN
# LHA_IS94_013	UNKN
# LHA_IS95_013	UNKN
# LHA_IS96_013	UNKN

# nearshore projects in the amst that do not appear to be in project tracker:

# PRJ_CD	protocol
# LHA_IA09_259	SMIN
# LHA_IA09_261	UNKN
# LHA_IA10_262	SMIN
# LHA_IA11_300	EF
# LHA_IA14_249	SMIN


prj_cds = ["LHA_IA13_RND", "LHA_IA11_LEG", "LHA_IA12_LEG", "LHA_IA13_LEG"]

project_type = ProjectType.objects.get(project_type="Synthesis")

for prj_cd in prj_cds:
    project = project_cache.get(prj_cd)
    project.project_type = project_type
    project.save()


protocol_cache = {x.abbrev: x for x in ProjectProtocol.objects.all()}

missing_projects = []
missing_protocols = []
for item in todos:
    project = project_cache.get(item[0])
    protocol = protocol_cache.get(item[1])
    if project is None:
        missing_projects.append(item[0])
    if protocol is None:
        missing_protocols.append(item[1])
    if protocol and project:
        project.protocol = protocol
        project.project_type = protocol.project_type
        project.save()

print("{} missing projects".format(len(missing_projects)))
print("{} missing protocols".format(len(missing_protocols)))

# ptype = projecttype_cache.get("Synthesis and Analysis")
# project = project_cache.get("LHA_FA16_MAT")
# project.project_type = ptype
# project.save()

todos = [
    ("LHA_IA13_RND", "SAA"),
    ("LHA_IA13_LEG", "SAA"),
    ("LHA_IA12_LEG", "SAA"),
    ("LHA_IA11_LEG", "SAA"),
    ("LHA_FA16_MAT", "SAA"),
]

todos = [
    ("LHA_AR16_001", "NFSR"),
    ("LHA_AR17_001", "NFSR"),
    ("LHA_AR18_001", "NFSR"),
    ("LHA_AR19_DEP", "SSA"),
    ("LHA_AR19_001", "NFSR"),
    ("LHA_AS14_081", "AE"),
    ("LHA_AS15_091", "AE"),
    ("LHA_AS15_081", "AE"),
    ("LHA_AS17_334", "AE"),
    ("LHA_BN00_001", "BEN"),
    ("LHA_BN01_001", "BEN"),
    ("LHA_BN02_001", "BEN"),
    ("LHA_BN03_001", "BEN"),
    ("LHA_BN04_001", "BEN"),
    ("LHA_BN05_001", "BEN"),
    ("LHA_BN07_001", "BEN"),
    ("LHA_BN08_001", "BEN"),
    ("LHA_BN09_001", "BEN"),
    ("LHA_BS96_101", "BS"),
    ("LHA_BS97_101", "BS"),
    ("LHA_BS05_101", "BS"),
    ("LHA_BS06_101", "BS"),
    ("LHA_CW09_001", "CWT"),
    ("LHA_IL17_T05", "WFTW"),
    ("LHA_IL17_T07", "WFTW"),
    ("LHA_IL18_T05", "WFTW"),
    ("LHA_IL19_T05", "WFTW"),
    ("LHA_SC93_005", "SC"),
    ("LHA_SC03_111", "SCR"),
    ("LHA_SC03_110", "SCA"),
    ("LHA_SC01_401", "SFD"),
    ("LHA_SS06_001", "SS"),
    ("LHA_SS07_001", "SS"),
    ("LHA_SS08_001", "SS"),
    ("LHA_SS09_001", "SS"),
    ("LHA_SS10_001", "SS"),
    ("LHA_SS11_001", "SS"),
    ("LHA_VC02_001", "SF"),
    ("LHA_XF01_031", "LSA"),
    ("LHA_XF15_031", "LSA"),
    ("LHA_XF16_031", "LSA"),
    ("LHA_XF17_031", "LSA"),
    ("LHA_XF18_031", "LSA"),
    ("LHA_XF19_031", "LSA"),
]


projects = Project.all_objects.filter(
    project_type__project_type="Sport Fish Collection"
)

protocol = protocol_cache.get("SF")

for project in projects:
    project.protocol = protocol
    project.project_type = protocol.project_type
    project.save()


projects = Project.all_objects.filter(protocol__abbrev="SCR").filter(
    prj_nm__icontains="access"
)

protocol = protocol_cache.get("SCA")
for project in projects:
    project.protocol = protocol
    project.save()


projects = Project.all_objects.filter(protocol__abbrev="SF").filter(
    prj_nm__icontains="volunteer"
)
protocol = protocol_cache.get("CVC")
for project in projects:
    project.protocol = protocol
    project.save()

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db import connection
from django.db.models import Count, F
from pjtk2.models import Project

term = "maxilla"
query_count0 = len(connection.queries)
projects = Project.objects.annotate(
    search=SearchVector("prj_nm", "abstract", "comment")
).filter(search=SearchQuery(term))

projects.count()
print("found {} projects".format(projects.count()))


query_count0 = len(connection.queries)
# calculate our facets by lake:
lakes = (
    projects.select_related("lake")
    .all()
    .values(lakeName=F("lake__lake_name"), lakeAbbrev=F("lake__abbrev"))
    .order_by("lakeName")
    .annotate(N=Count("lakeName"))
)
print("By Lakes:")
for x in lakes:
    print(x)
query_count1 = len(connection.queries)
print("queries run: {}".format((query_count1 - query_count0)))


project_types = (
    projects.select_related("project_type")
    .all()
    .values("project_type__project_type")
    .order_by("project_type")
    .annotate(N=Count("project_type"))
)

print("By Project Type:")
for x in project_types:
    print(x)


project_scope = (
    projects.select_related("project_type")
    .all()
    .values(projScope=F("project_type__scope"))
    .order_by("project_type__scope")
    .annotate(N=Count("project_type__scope"))
)
scope_lookup = dict(ProjectType.PROJECT_SCOPE_CHOICES)
for scope in project_scope:
    scope["name"] = scope_lookup.get(scope["projScope"])


print("By Project Scope:")
for x in project_scope:
    print(x)


project_field_component = (
    projects.select_related("project_type")
    .all()
    .values("project_type__field_component")
    .order_by("project_type__field_component")
    .annotate(N=Count("project_type__field_component"))
)
print("Field Component")
for x in project_field_component:
    print(x)

query_count1 = len(connection.queries)
print("queries run: {}".format((query_count1 - query_count0)))


protocols = (
    projects.select_related("protocol")
    .all()
    .values(projProtocol=F("protocol__protocol"), protocolAbbrev=F("protocol__abbrev"))
    .order_by("protocol")
    .annotate(N=Count("protocol"))
)
print("Protocols")
for x in protocols:
    print(x)

query_count1 = len(connection.queries)
print("queries run: {}".format((query_count1 - query_count0)))


import psycopg2

con_pars = {
    "HOST": "localhost",
    "NAME": "superior",
    "USER": os.getenv("PGUSER"),
    "PASSWORD": os.getenv("PGPASS"),
}

pg_constring = "host='{HOST}' dbname='{NAME}' user='{USER}'" + " password='{PASSWORD}'"
pg_constring = pg_constring.format(**con_pars)

pg_conn = psycopg2.connect(pg_constring)
pg_cur = pg_conn.cursor()


sql = "select prj_cd, comment from pjtk2_project where year='2019'"
pg_cur.execute(sql)
abstracts = pg_cur.fetchall()


for item in abstracts:
    proj = Project.objects.get(prj_cd=item[0])
    proj.abstract = item[1]
    proj.save()
print("done!")


import csv

# now to get the lake erie and lake ontario creel points:
import django_settings
from django.contrib.gis.geos import GEOSGeometry
from pjtk2.models import Project, SamplePoint

# csv_file = "C:/Users/COTTRILLAD/1work/Python/djcode/apps/pjtk2/utilities/glb_data/LEMU_SC_Points.csv"
# csv_file = "C:/Users/COTTRILLAD/1work/Python/djcode/apps/pjtk2/utilities/glb_data/LOMU_SC_Points.csv"
# csv_file = "C:/Users/COTTRILLAD/1work/ScrapBook/project_tracker/pjtk2_sample_points.csv"
csv_file = "C:/Users/COTTRILLAD/1work/ScrapBook/project_tracker/pjtk2_sample_points/superior_points.txt"

points = []

with open(csv_file, newline="") as csvfile:
    reader = csv.reader(csvfile)
    next(reader, None)  # skip header
    for row in reader:
        x = [row[0], row[1], float(row[2]), float(row[3])]
        points.append(x)

# create a cache for projects
prj_cds = list(set([x[0] for x in points]))
project_cache = {x.prj_cd: x for x in Project.objects.filter(prj_cd__in=prj_cds)}

# now loop over our points, create a sample point, get the associated
# project, and add the point to our list of item to create:

items = []

for pt in points:
    proj = project_cache.get(pt[0])
    if proj is None:
        print("Unable to find project: {}".format(pt[0]))
        continue
    label = pt[1].replace("{} - ".format(pt[0]), "")
    ddlat = pt[2]
    ddlon = pt[3]
    geom = GEOSGeometry("POINT({} {})".format(ddlon, ddlat))
    sample_point = SamplePoint(project=proj, label=label, geom=geom)
    items.append(sample_point)

SamplePoint.objects.bulk_create(items)

# update the assocaited geomeries of our project so we find them in spatial searches:
for prj_cd, project in project_cache.items():
    project.update_convex_hull()
    project.update_multipoints()
print("Done!")


# users (get or create)
# employee
# milestone
# project type
# project Protocol
# database
# funding source (essentailly a m2m with project throgh projectfunding)
# Project
# projectImages
# projectFunding
# samplePoint
# projectmilestones
# report
# associatedFile
# bookmark
# family
# projectsisters
# message
# message2user


import sys

from django.core import serializers
from pjtk2.models import (
    Database,
    FundingSource,
    Milestone,
    ProjectProtocol,
    ProjectType,
)


def migrate(model, size=500, start=0):
    count = model.objects.using("default").count()
    print("{} objects in model {}.".format(count, model))
    for i in range(start, count, size):
        print(i)
        sys.stdout.flush()
        original_data = model.objects.using("default").all()[i : i + size]
        original_data_json = serializers.serialize("json", original_data)
        new_data = serializers.deserialize("json", original_data_json, using="gldjango")
        for n in new_data:
            n.save(using="gldjango")


# load users and employees manually

migrate(Milestone)
migrate(ProjectType)

migrate(ProjectProtocol)
migrate(Database)
migrate(FundingSource)


# Users and employees are a little tougher - they use custom user objects


from django.contrib.auth import get_user_model

User = get_user_model()

original_data = Employee.objects.all()[:10]
original_data_json = serializers.serialize("json", original_data)


# I need all of the project milestones from my completed projects in the last 5 years,
# including the project lead, and proejct type
import django_settings
from django.contrib.auth import get_user_model
from django.db import connection
from pjtk2.models import Milestone, Project, ProjectMilestones, ProjectType

User = get_user_model()

employees = User.objects.filter(username="cottrillad")
this_year = 2020


query_count0 = len(connection.queries)
completed = (
    Project.objects.completed()
    .filter(owner__pk__in=employees)
    .filter(year__gte=this_year - 15)
).values_list("pk")
len(completed)

# completed = Project.objects.filter(prj_cd__in=["LHA_IA09_002", "LHA_IA10_002"])
# proj_ms = (
#     ProjectMilestones.objects.select_related("project")
#     .exclude(milestone__label="Submitted")
#     .filter(project__pk__in=completed)
#     .prefetch_related("project__project_type", "project__prj_ldr")
# )

# this could be genric utilyt function = pass in a list of project_id's
# and get a list of dictionaries containing the status of the
# milestones associated with each project.


# what we need is a dictionary with keys:
# project
# + Project Attrs:
# project code, project name, url, project type, project lead
# + milestones (pre-populate with milestone keys):
# each milestone: report/milestone
# required - True/False
# completed - True/False


milestones = [
    x[0]
    for x in (
        Milestone.objects.filter(category="Core")
        .order_by("order")
        .exclude(label__in=["Submitted", "Cancelled"])
        .values_list("label")
    )
]


completed_projects = (
    Project.objects.completed()
    .filter(owner__pk__in=employees)
    .filter(year__gte=this_year - 15)
).values_list("pk")

prj_milestones = get_proj_ms(completed_projects)

completed = make_proj_ms_dict(prj_milestones, milestones)


# query_count1 = len(connection.queries)
# print("queries run: {}".format((query_count1 - query_count0)))

milestones = (
    Milestone.objects.filter(category="Core")
    .exclude(label__in=["Approved", "Submitted", "Cancelled", "Sign off"])
    .order_by("order")
    .all()
)

project_milestones = (
    ProjectMilestones.objects.select_related("project", "milestone")
    # .exclude(
    #    milestone__label__in=["Approved", "Submitted", "Cancelled", "Sign off"]
    # )
    .filter(milestone__in=milestones)
    .filter(project__prj_cd="LHA_FS16_001")
    .prefetch_related("project__project_type", "project__prj_ldr")
    .order_by("-project__year", "project__prj_cd", "milestone__order")
    .values(
        "project__prj_cd",
        "project__prj_nm",
        "project__year",
        "project__slug",
        "project__prj_ldr__first_name",
        "project__prj_ldr__last_name",
        "project__prj_ldr__username",
        "project__project_type__project_type",
        "milestone__category",
        "milestone__report",
        "milestone__label",
        "required",
        "completed",
    )
)

for ms in project_milestones:
    print(
        ms["milestone__label"], ms["milestone__report"], ms["required"], ms["completed"]
    )


for k, v in x["LHA_FS16_001"]["milestones"].items():
    print(k, "\t", v["required"], "\t", v["completed"], "\t", v["status"])
