from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^activate', views.activate, name='activate'),
    url(r'^warm_up', views.warm_up, name='warm_up'),
    url(r'^$', views.query, name='query'),
]
