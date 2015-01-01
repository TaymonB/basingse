"""
Django settings for basingse project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

import os

from django.core.exceptions import ImproperlyConfigured
from django.core.signing import Signer
import environ

root = environ.Path(__file__) - 2
env = environ.Env()
if os.path.exists(root('.env')):
    environ.Env.read_env(root('.env'))

# Development vs. production mode
DEBUG = TEMPLATE_DEBUG = env('DEBUG', bool, False)

# Database
DATABASES = {'default': env.db()}

# Serving static media files
STATIC_ROOT = root('static/')

# Security
SECRET_KEY = env('SECRET_KEY')
PUBLIC_UNIQUE_ID = Signer().signature('basingse')
if not DEBUG:
    ALLOWED_HOSTS = env('ALLOWED_HOSTS', list)
    if env('HTTP_X_FORWARDED_PROTO', bool, False):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Internationalization, etc.
LANGUAGE_CODE = env('LANGUAGE_CODE')
TIME_ZONE = env('TIME_ZONE')

# Email
globals().update(env.email_url())
if EMAIL_HOST and EMAIL_HOST != 'localhost':
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
else:
    DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', str, 'webmaster@localhost')

# System administration
ADMINS = tuple(tuple(admin.split(':', 1)) for admin in env('ADMINS', list, []))
try:
    MANAGERS = tuple(tuple(manager.split(':', 1)) for manager in env('MANAGERS', list))
except ImproperlyConfigured:
    MANAGERS = ADMINS
SERVER_EMAIL = env('SERVER_EMAIL', str,
                   'root@localhost' if DEFAULT_FROM_EMAIL == 'webmaster@localhost' else DEFAULT_FROM_EMAIL)

# Elastichosts API
ELASTICHOSTS_API_ENDPOINT = env('EHURI')
ELASTICHOSTS_API_CREDENTIALS = tuple(env('EHAUTH').split(':', 1))

# The rest of this stuff doesn't depend on deployment settings.

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'uservm',
)

MIDDLEWARE_CLASSES = (
#    'sslify.middleware.SSLifyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'basingse.urls'
WSGI_APPLICATION = 'basingse.wsgi.application'

TEMPLATE_DIRS = [root('templates')]

STATIC_URL = '/static/'

if not DEBUG:
    pass#CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE = True

USE_I18N = USE_L10N = USE_TZ = True

LOGIN_REDIRECT_URL = 'uservm.views.home'

EMAIL_SUBJECT_PREFIX = 'Ba Sing Se: '

CRISPY_TEMPLATE_PACK = 'bootstrap3'
