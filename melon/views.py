from django.views.generic import ListView
from .models import Song


class SongListView(ListView):
    model = Song
    queryset = Song.objects.all()
    paginate_by = 10

    template_name = 'melon/song_list.html'

    def get_template_names(self):
        if self.request.headers.get('HX-Request') == 'true':
            return ['melon/_song_list.html']
        return [self.template_name]


song_list = SongListView.as_view()
