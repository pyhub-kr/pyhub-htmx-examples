from django.views.generic import ListView
from .models import Song


class SongListView(ListView):
    model = Song
    queryset = Song.objects.all()
    paginate_by = 10


song_list = SongListView.as_view()
