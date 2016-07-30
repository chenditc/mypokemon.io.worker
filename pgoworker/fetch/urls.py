from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^activate', views.activate, name='activate'),
    url(r'^$', views.query, name='query'),
]
