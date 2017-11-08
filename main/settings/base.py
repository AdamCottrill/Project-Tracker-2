# Django settings for pjtk2 project.

import os

PROJECT_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '../..'))

#these are from Kennith Love's best practices
here = lambda * x: os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)
root = lambda * x: os.path.join(os.path.abspath(PROJECT_ROOT), *x)

DEBUG = True


ADMINS = (
    ('Adam Cottrill', 'racottrill@bmts.com'),
)

MANAGERS = ADMINS

##username and password: cottrillad, django
#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': '%s/db/pjtk2.db' % root(),
#    }
#}

#print 'database name: %s/db/pjtk2.db' % root()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Detroit'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = root("uploads/")

#print "MEDIA_ROOT = %s" % MEDIA_ROOT

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
#MEDIA_URL = root()
#MEDIA_URL = 'uploads/'
MEDIA_URL = 'milestone_reports/'
# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"

ADMIN_MEDIA_PREFIX = '/admin/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = root("static_root/")
#STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static_root')
#STATIC_ROOT = ""
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    # root('/pjtk2/static/'),
    #os.path.abspath(os.path.join(PROJECT_ROOT, 'static/'))
    #'C:/1work/Python/djcode/pjtk2/static/',
    os.path.join(PROJECT_ROOT, 'static'),

)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '0yo*&amp;!557a9o8=+2b_9mrcfc=n$*7vc-hr@b56y^x#&amp;a+pidx@'


MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    #'main.middleware.LoginRequiredMiddleware',
    'pagination.middleware.PaginationMiddleware',
)



ROOT_URLCONF = 'main.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'main.wsgi.application'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            root('templates'),
            root('pjtk2/templates'),
            root('simple_auth/templates'),
            root('tickets/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]



DJANGO_APPS = (
    'django.contrib.auth',
    'django.contrib.staticfiles',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.gis',
)

THIRDPARTY_APPS = (
    'crispy_forms',
    'django_filters',
    'taggit',
    'haystack',
    'passwords',
    'password_reset',
    'pagination',
    'olwidget',
    )

CRISPY_FAIL_SILENTLY = not DEBUG

MY_APPS = (
    'tickets',
    'simple_auth',
    'pjtk2',
    )

INSTALLED_APPS = DJANGO_APPS + THIRDPARTY_APPS + MY_APPS


##HAYSTACK_CONNECTIONS = {
##    'default': {
##        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
##        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_ndex'),
##    },
##}

eng = 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine'
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': eng,
        'URL': 'http://127.0.0.1:9200/',
        'INDEX_NAME': 'haystack',
    },
}


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

CRISPY_TEMPLATE_PACK = 'bootstrap3'

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/accounts/login/'

POSTGIS_VERSION = ( 2, 1, 2 )

LINK_PATTERNS = [{'pattern':
                  r'project: ?([a-zA-Z]{3}\_[a-zA-Z]{2}\d{2}\_[a-zA-Z0-9]{3})',
                  'url': r'<a href="/projects/projectdetail/{0}">{1}</a>'},
                 {'pattern': r'ticket:\s?(\d+)',
                  'url': r'<a href="/tickets/\1">ticket \1</a>'}]
