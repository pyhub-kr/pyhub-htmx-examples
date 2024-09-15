from django.db import models


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Song(models.Model):
    song_id = models.BigIntegerField(unique=True, verbose_name="곡일련번호")
    rank = models.IntegerField(verbose_name="순위")
    album_id = models.BigIntegerField(verbose_name="album_uid")
    album_name = models.CharField(max_length=255, verbose_name="album_name")
    title = models.CharField(max_length=255, verbose_name="곡명")
    artist_id = models.BigIntegerField(verbose_name="artist_uid")
    artist_name = models.CharField(max_length=255, verbose_name="artist_name")
    album_cover_url = models.URLField(verbose_name="커버이미지_주소")
    lyrics = models.TextField(verbose_name="가사")
    genres = models.ManyToManyField(Genre, related_name="songs", verbose_name="장르")
    release_date = models.DateField(verbose_name="발매일")
    likes = models.IntegerField(verbose_name="좋아요")

    class Meta:
        ordering = ["rank"]
        verbose_name = "노래"
        verbose_name_plural = "노래들"

    def __str__(self):
        return f"{self.rank}. {self.title} - {self.artist_name}"
