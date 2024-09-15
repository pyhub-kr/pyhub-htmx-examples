import json
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from melon.models import Song, Genre


class Command(BaseCommand):
    help = "Import Melon chart data from JSON file"

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the JSON file")

    def handle(self, *args, **options):
        json_file = options["json_file"]

        with open(json_file, "r", encoding="utf-8") as file:
            data = json.load(file)

        with transaction.atomic():
            for song_data in data:
                song, created = Song.objects.update_or_create(
                    song_id=song_data["곡일련번호"],
                    defaults={
                        "rank": int(song_data["순위"]),
                        "album_id": song_data["album_uid"],
                        "album_name": song_data["album_name"],
                        "title": song_data["곡명"],
                        "artist_id": song_data["artist_uid"],
                        "artist_name": song_data["artist_name"],
                        "album_cover_url": song_data["커버이미지_주소"],
                        "lyrics": song_data["가사"],
                        "release_date": datetime.strptime(
                            song_data["발매일"], "%Y-%m-%d"
                        ).date(),
                        "likes": song_data["좋아요"],
                    },
                )

                # Clear existing genres and add new ones
                song.genres.clear()
                for genre_name in song_data["장르"]:
                    genre, _ = Genre.objects.get_or_create(name=genre_name)
                    song.genres.add(genre)

                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created song: {song}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Updated song: {song}"))

        self.stdout.write(self.style.SUCCESS("Successfully imported Melon chart data"))
