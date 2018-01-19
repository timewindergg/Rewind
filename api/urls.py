from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from api import views

urlpatterns = [
    url(r'^get_match_timeline/$', views.get_match_timeline),
    url(r'^get_summoner/$', views.get_summoner),
    url(r'^get_match_history/$', views.get_match_history),
    url(r'^get_user_champion_stats/$', views.get_user_champion_stats),
    url(r'^get_current_match/$', views.get_current_match),
    url(r'^get_current_match_details/$', views.get_current_match_details),
    url(r'^update_summoner/$', views.update_summoner),
    url(r'^get_version/$', views.get_version),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
