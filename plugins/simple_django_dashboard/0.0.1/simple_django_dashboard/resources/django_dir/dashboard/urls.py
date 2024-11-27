from django.views.generic import RedirectView

from . import views
from django.urls import path

urlpatterns = [
    path('', views.root, name='root'),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True))
]