from django.urls import path

from graph import views

urlpatterns = [
    path('', views.index, name='index' ),
]
