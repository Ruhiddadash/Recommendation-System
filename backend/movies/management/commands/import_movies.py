import csv
import re
from django.core.management.base import BaseCommand
from movies.models import Movie

class Command(BaseCommand):
    help = "Import movies from movies.csv into the database"

    def handle(self, *args, **kwargs):
        file_path = "movies/data/movies.csv"

        Movie.objects.all().delete()

        with open(file_path, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            count = 0

            for row in reader:
                raw_title = row.get("title", "")

                match = re.search(r"\((\d{4})\)", raw_title)
                year = int(match.group(1)) if match else None

                clean_title = re.sub(r"\(\d{4}\)", "", raw_title).strip()

                Movie.objects.create(
                    movieId=int(row["movieId"]),
                    title=clean_title,
                    genres=row.get("genres", ""),
                    year=year,
                )

                count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} movies imported successfully!"))
