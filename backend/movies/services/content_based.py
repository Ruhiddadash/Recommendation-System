import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors
from movies.models import Movie

class ContentBasedRecommender:
    _instance = None  # Singleton

    def __new__(cls):
        # Singleton: sadece bir instance oluştur
        if cls._instance is None:
            cls._instance = super(ContentBasedRecommender, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Load movies from DB
        movies = pd.DataFrame(
            list(Movie.objects.all().values(
                "id", "title", "genres", "description", "director", "actors"
            ))
        )

        movies = movies.fillna("")
        movies['genres'] = movies['genres'].str.replace("|", " ", regex=False)

        movies['metadata'] = (
            movies['title'] + " " +
            movies['genres'] + " " +
            movies['description'] + " " +
            movies['director'] + " " +
            movies['actors']
        )

        self.movies = movies
        self.model = SentenceTransformer(
            'all-MiniLM-L6-v2',
            device='cpu'
        )
        self.embeddings = self.model.encode(
            movies['metadata'].tolist(),
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        self.nn = NearestNeighbors(
            n_neighbors=20,
            metric='cosine',
            algorithm='brute'
        )

        self.nn.fit(self.embeddings)

        self._initialized = True

    def recommend_by_movie_id(self, movie_id, n=10):
        row = self.movies[self.movies['id'] == movie_id]
        if row.empty:
            return []

        idx = row.index[0]

        dist, ind = self.nn.kneighbors(
            self.embeddings[idx].reshape(1, -1),
            n_neighbors=n+1
        )

        result_indices = [
            i for i in ind.flatten() if i != idx
        ][:n]

        return self.movies.iloc[result_indices][['id', 'title', 'genres']].to_dict("records")
