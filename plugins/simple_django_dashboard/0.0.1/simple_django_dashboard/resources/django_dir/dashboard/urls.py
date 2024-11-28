from django.views.generic import RedirectView

from . import views
from django.urls import path

urlpatterns = [
    path('', views.root, name='root'),
]