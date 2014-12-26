from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from uservm import urls as uservm_urls

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'basingse.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', auth_views.login),
    url(r'^$', include(uservm_urls)),
)
