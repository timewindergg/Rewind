from django.conf.urls import url
from api import views

urlpatterns = [
    url(r'^test/$', views.test),
    url(r'^get_match_timeline/$', views.get_match_timeline),

]
