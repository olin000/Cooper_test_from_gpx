"""
URL configuration for cooper_test_from_gpx project.
"""
from django.contrib import admin
from django.urls import path

import apps.fileloader.views
import apps.gpxreader.views

urlpatterns = [
    path('', apps.fileloader.views.loadfile, name='fileloader'),
    path('fileloader/', apps.fileloader.views.loadfile, name='fileloader'),
    path('chart/', apps.gpxreader.views.readgpx, name='gpxreader'),
    path('admin/', admin.site.urls),
]
