from django.conf.urls import patterns, include, url

from uservm import views

urlpatterns = patterns('',
    url(r'^$', views.home),
    url(r'^status$', views.status),
    url(r'^start$', views.start),
    url(r'^stop$', views.stop),
    url(r'^shutdown$', views.shutdown),
    url(r'^reset$', views.reset),
    url(r'^heartbeat$', views.heartbeat),
)
