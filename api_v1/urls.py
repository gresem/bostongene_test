from django.conf.urls import include, url
from api_v1 import views

document_pattern = [
    url(r'^send_url/$', views.NewDocument.as_view(), name='document_send_url'),
    url(r'^get_md5/$', views.Md5.as_view(), name='document_get_md5')
]

urlpatterns = [
    url(r'^document/', include(document_pattern)),
]