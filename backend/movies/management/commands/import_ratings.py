import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from movies.models import Movie, UserMovieRating


class Command(BaseCommand):
    help = "Fast import of ratings.csv into UserMovieRating table"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, default="ratings.csv")

    def handle(self, *args, **options):
        file_path = options["file"]
        self.stdout.write(self.style.SUCCESS(f"Loading ratings from: {file_path}"))

        # --------------------
        # Step 1: Load movies into dict
        # --------------------
        movies = Movie.objects.all().values("movieId", "id")
        movie_map = {m["movieId"]: m["id"] for m in movies}

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(movie_map)} movies."))

        # --------------------
        # Step 2: Load users into dict (existing ones)
        # --------------------
        users = User.objects.all().values("id")
        existing_user_ids = {u["id"] for u in users}

        new_users = []
        ratings_to_create = []

        skipped = 0

        # --------------------
        # Step 3: Read CSV in one pass
        # --------------------
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                user_id = int(row["userId"])
                movieId = int(row["movieId"])
                rating_val = float(row["rating"])

                # Skip ratings for movieId that does not exist
                if movieId not in movie_map:
                    skipped += 1
                    continue

                # Collect new users to create
                if user_id not in existing_user_ids:
                    new_users.append(
                        User(id=user_id, username=f"user_{user_id}")
                    )
                    existing_user_ids.add(user_id)

                # Round to 1–5 integer scale (optional)
                rating_round = round(rating_val)

                ratings_to_create.append(
                    UserMovieRating(
                        user_id=user_id,
                        movie_id=movie_map[movieId],
                        rating=rating_round,
                    )
                )

        # --------------------
        # Step 4: Bulk create new users
        # --------------------
        if new_users:
            User.objects.bulk_create(new_users, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(
                f"Created {len(new_users)} new users."
            ))
        else:
            self.stdout.write(self.style.HTTP_INFO("No new users."))

        # --------------------
        # Step 5: Bulk create ratings
        # --------------------
        UserMovieRating.objects.all().delete()  # optional: clean table first
        UserMovieRating.objects.bulk_create(ratings_to_create, batch_size=5000)

        self.stdout.write(self.style.SUCCESS(
            f"Inserted ratings: {len(ratings_to_create)}"
        ))
        self.stdout.write(self.style.WARNING(
            f"Skipped rows (missing movie): {skipped}"
        ))
        self.stdout.write(self.style.SUCCESS("Import finished successfully!"))
