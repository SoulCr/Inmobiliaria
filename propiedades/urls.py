from django.urls import path

from . import views

app_name = "propiedades"

urlpatterns = [
    path("", views.listado, name="listado"),
    path("propiedad/<int:pk>/", views.detalle, name="detalle"),
    path("api/consultas/", views.api_consulta, name="api_consulta"),
]
