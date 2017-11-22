from django.conf.urls import url
from api import views

urlpatterns = [
    url(r'^get_match_timeline/$', views.get_match_timeline),
    url(r'^get_summoner/$', views.get_summoner),
    url(r'^get_match_history/$', views.get_match_history),
    url(r'^get_user_champion_stats/$', views.get_user_champion_stats),
    url(r'^get_current_match/$', views.get_current_match),
    url(r'^update_summoner/$', views.update_summoner),
]
