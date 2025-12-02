# movies/recommenders/contentbased.py
import os
import pickle
import threading
from typing import List, Dict, Union

import numpy as np
from django.conf import settings
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
from movies.models import Movie

# Where to store pickled artifacts
ARTIFACT_DIR = os.path.join(settings.BASE_DIR, "movie_recommender_artifacts")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

EMBEDDINGS_PKL = os.path.join(ARTIFACT_DIR, "content_embeddings.pkl")
NN_MODEL_PKL = os.path.join(ARTIFACT_DIR, "content_nn_model.pkl")
METADATA_PKL = os.path.join(ARTIFACT_DIR, "content_metadata.pkl")

# Model name (change if you want a different SBERT model)
SENTENCE_TRANSFORMER_MODEL = "all-MiniLM-L6-v2"

# Thread lock to prevent concurrent rebuilds in production
_build_lock = threading.Lock()


def _build_and_persist():
    """
    Build embeddings and NN model from movies table and persist artifacts to disk.
    This is an expensive operation and is intended to be run once (or via a management command).
    """
    with _build_lock:
        # If artifacts already exist (race condition), skip
        if all(os.path.exists(p) for p in (EMBEDDINGS_PKL, NN_MODEL_PKL, METADATA_PKL)):
            return

        # Load movies from DB
        qs = Movie.objects.all().order_by("id")
        if not qs.exists():
            raise RuntimeError("No movies in DB to build the content-based model.")

        titles = []
        genres = []
        movie_ids = []
        tags_field = []  # if you have extra tags in Movie model
        # Build metadata string for each movie
        for m in qs:
            movie_ids.append(int(m.id))
            titles.append(str(m.title))
            genres.append(str(m.genres or ""))
            # if you have a tags column in model, include it; else keep empty
            tags_field.append(str(getattr(m, "tag", "") or ""))

        # Create metadata: title + genres (pipe separated replaced) + tags
        metadata = []
        for t, g, tg in zip(titles, genres, tags_field):
            g_clean = g.replace("|", " ") if isinstance(g, str) else ""
            md = f"{t} {g_clean} {tg}"
            metadata.append(md)

        # Load sentence transformer and compute embeddings
        model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        # encode normalizes if normalize_embeddings; we'll normalize later
        embeddings = model.encode(metadata, convert_to_numpy=True, show_progress_bar=True)
        # Normalize embeddings to unit vectors (cosine similarity works better)
        embeddings = normalize(embeddings, axis=1)

        # Fit a NearestNeighbors model (brute force fine for small-medium scale; you can swap for faiss later)
        nn = NearestNeighbors(n_neighbors=50, metric="cosine", algorithm="brute")
        nn.fit(embeddings)

        # Persist artifacts
        with open(EMBEDDINGS_PKL, "wb") as f:
            pickle.dump(embeddings, f, protocol=pickle.HIGHEST_PROTOCOL)
        with open(NN_MODEL_PKL, "wb") as f:
            pickle.dump(nn, f, protocol=pickle.HIGHEST_PROTOCOL)
        # store metadata mapping
        metadata_obj = {
            "movie_ids": movie_ids,      # list index -> Movie.id
            "titles": titles,            # parallel list
            "genres": genres,
        }
        with open(METADATA_PKL, "wb") as f:
            pickle.dump(metadata_obj, f, protocol=pickle.HIGHEST_PROTOCOL)


def _load_artifacts():
    """
    Load persisted artifacts. Returns (embeddings, nn_model, metadata_obj)
    Raises FileNotFoundError if artifacts don't exist.
    """
    if not (os.path.exists(EMBEDDINGS_PKL) and os.path.exists(NN_MODEL_PKL) and os.path.exists(METADATA_PKL)):
        raise FileNotFoundError("Content-based artifacts not found. Run build first.")

    with open(EMBEDDINGS_PKL, "rb") as f:
        embeddings = pickle.load(f)
    with open(NN_MODEL_PKL, "rb") as f:
        nn = pickle.load(f)
    with open(METADATA_PKL, "rb") as f:
        metadata = pickle.load(f)

    return embeddings, nn, metadata


# Keep artifacts in memory for faster access (lazy load)
_ARTIFACTS = {
    "embeddings": None,
    "nn": None,
    "metadata": None,
    "model": None,   # SentenceTransformer instance (optional, used for incremental queries)
}


def ensure_artifacts_ready(rebuild_if_missing: bool = True):
    """
    Ensure artifacts are available in memory. Builds them if missing (if rebuild_if_missing True).
    """
    if _ARTIFACTS["embeddings"] is not None:
        return

    try:
        embeddings, nn, metadata = _load_artifacts()
    except FileNotFoundError:
        if rebuild_if_missing:
            _build_and_persist()
            embeddings, nn, metadata = _load_artifacts()
        else:
            raise

    _ARTIFACTS["embeddings"] = embeddings
    _ARTIFACTS["nn"] = nn
    _ARTIFACTS["metadata"] = metadata

    # instantiate sentence-transformer model lazily (for encoding new queries)
    if _ARTIFACTS["model"] is None:
        _ARTIFACTS["model"] = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)


def build_and_save_model():
    """
    Public helper to force-build artifacts from DB. Call via a management command or shell.
    """
    _build_and_persist()
    # clear in-memory cache so next call loads pickles
    _ARTIFACTS["embeddings"] = None
    _ARTIFACTS["nn"] = None
    _ARTIFACTS["metadata"] = None
    _ARTIFACTS["model"] = None
    # load into memory
    ensure_artifacts_ready(rebuild_if_missing=False)


def _ids_to_indices(selected: List[Union[int, str]], metadata: dict):
    """
    Accept a list of Movie.id values (int) or movie title strings.
    Returns list of indices corresponding to artifacts arrays.
    """
    movie_ids = metadata["movie_ids"]
    titles = metadata["titles"]

    id_to_index = {mid: idx for idx, mid in enumerate(movie_ids)}
    title_to_index = {t.lower(): idx for idx, t in enumerate(titles)}

    indices = []
    for s in selected:
        if isinstance(s, int):
            if s in id_to_index:
                indices.append(id_to_index[s])
        elif isinstance(s, str):
            key = s.strip().lower()
            # exact match
            if key in title_to_index:
                indices.append(title_to_index[key])
            else:
                # partial match: first that contains substring
                found = next((i for i, t in enumerate(titles) if key in t.lower()), None)
                if found is not None:
                    indices.append(found)
        # ignore unknown entries
    return indices


def recommend_content_based(selected_ids: List[Union[int, str]],
                            top_k: int = 10,
                            user=None) -> List[Dict]:
    """
    Main function to call from views:
    - selected_ids: list of Movie.id integers OR movie title strings (1..4 typically)
    - top_k: number of desired recommendations (default 10)
    - user: optional Django User (if you want personalization later)

    Returns: list of dicts:
        [
            {"id": <Movie.id>, "title": "...", "genres": "...", "score": 0.873},
            ...
        ]
    """

    # ensure model artifacts are ready (build if missing)
    ensure_artifacts_ready(rebuild_if_missing=True)

    embeddings = _ARTIFACTS["embeddings"]
    nn = _ARTIFACTS["nn"]
    metadata = _ARTIFACTS["metadata"]
    model = _ARTIFACTS["model"]

    # Map provided selected_ids into indices in embeddings array
    indices = _ids_to_indices(selected_ids, metadata)
    if not indices:
        # If user passed invalid ids/titles, return empty list
        return []

    # Compute aggregated embedding: average of selected embeddings
    selected_embs = embeddings[indices]
    if selected_embs.ndim == 1:
        avg_emb = selected_embs.reshape(1, -1)
    else:
        avg_emb = np.mean(selected_embs, axis=0, keepdims=True)
    # normalize
    avg_emb = normalize(avg_emb, axis=1)

    # Query nearest neighbors
    # We ask for top_k + len(indices) to then exclude inputs
    n_query = min(50, top_k + len(indices) + 10)
    dists, inds = nn.kneighbors(avg_emb, n_neighbors=n_query)
    dists = np.asarray(dists).flatten()
    inds = np.asarray(inds).flatten()

    # Build recommendations excluding any input indices; collect until top_k
    recommendations = []
    seen = set(indices)
    for dist, idx in zip(dists, inds):
        if idx in seen:
            continue
        movie_id = metadata["movie_ids"][int(idx)]
        title = metadata["titles"][int(idx)]
        genre = metadata["genres"][int(idx)] if "genres" in metadata else ""
        # Convert NN cosine distance to similarity score: similarity = 1 - distance
        # (NearestNeighbors with metric "cosine" returns distances in [0, 2] but typically [0,1])
        score = float(max(0.0, 1.0 - float(dist)))
        recommendations.append({
            "id": int(movie_id),
            "title": title,
            "genres": genre,
            "score": round(score, 4)
        })
        if len(recommendations) >= top_k:
            break

    return recommendations
