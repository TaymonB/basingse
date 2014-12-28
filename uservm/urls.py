from django.conf.urls import patterns, include, url

from uservm import views

urlpatterns = patterns('',
    url(r'^$', views.home),
)
