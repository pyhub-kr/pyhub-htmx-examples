from django.contrib import admin
from .models import Song, Genre


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = (
        "rank",
        "title",
        "artist_name",
        "album_name",
        "release_date",
        "likes",
    )
    list_filter = ("release_date", "genres")
    search_fields = ("title", "artist_name", "album_name")
    readonly_fields = ("song_id", "album_id", "artist_id", "album_cover_url")
    filter_horizontal = ("genres",)

    fieldsets = (
        (
            "기본 정보",
            {"fields": ("song_id", "rank", "title", "artist_name", "artist_id")},
        ),
        (
            "앨범 정보",
            {"fields": ("album_name", "album_id", "album_cover_url", "release_date")},
        ),
        ("추가 정보", {"fields": ("genres", "lyrics", "likes")}),
    )


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
