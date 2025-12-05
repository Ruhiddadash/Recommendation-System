from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from django.contrib.auth.models import User

from movies.models import Movie, UserMovieRating


class DjangoCollaborativeFiltering:
    """
    User-based collaborative filtering recommender using DB ratings.
    Produces detailed trust metrics for increased recommendation transparency.

    NOTE (customization):
    - Ratings on the *currently selected movies* are considered more important.
      When computing user–user similarity, neighbors who have also rated the
      selected movies (and rate them similarly to the target user) receive
      a similarity boost. This makes the recommendations more reflective of
      the user's current choices.
    """

    def __init__(
        self,
        min_movie_ratings: int = 2,
        min_user_ratings: int = 2,
        k_neighbors: int = 30,
    ):
        self.min_movie_ratings = min_movie_ratings
        self.min_user_ratings = min_user_ratings
        self.k_neighbors = k_neighbors

        self.R: Optional[np.ndarray] = None
        self.user_ids: List[int] = []
        self.movie_ids: List[int] = []
        self.user_index: Dict[int, int] = {}
        self.movie_index: Dict[int, int] = {}
        self.user_means: Optional[np.ndarray] = None

        self.rating_count: int = 0

    # ==============================================================
    # MATRIX BUILD
    # ==============================================================

    def _build_matrix(self) -> None:
        qs = UserMovieRating.objects.values("user_id", "movie_id", "rating")
        df = pd.DataFrame.from_records(qs)
        if df.empty:
            raise ValueError("No ratings found.")

        self._build_matrix_from_df(df)
        self.rating_count = UserMovieRating.objects.count()

    def _build_matrix_from_df(self, df: pd.DataFrame) -> None:
        movie_counts = df["movie_id"].value_counts()
        user_counts = df["user_id"].value_counts()

        df = df[df["movie_id"].isin(movie_counts[movie_counts >= self.min_movie_ratings].index)]
        df = df[df["user_id"].isin(user_counts[user_counts >= self.min_user_ratings].index)]

        if df.empty:
            raise ValueError("Filtering removed too much data. CF cannot be built.")

        self.user_ids = sorted(df["user_id"].unique())
        self.movie_ids = sorted(df["movie_id"].unique())

        self.user_index = {uid: i for i, uid in enumerate(self.user_ids)}
        self.movie_index = {mid: j for j, mid in enumerate(self.movie_ids)}

        n_users = len(self.user_ids)
        n_movies = len(self.movie_ids)

        R = np.full((n_users, n_movies), np.nan, dtype=np.float32)

        for row in df.itertuples(index=False):
            u = self.user_index[row.user_id]
            m = self.movie_index[row.movie_id]
            R[u, m] = float(row.rating)

        self.R = R
        self.user_means = np.nanmean(self.R, axis=1)

    def _ensure_fresh(self) -> None:
        current = UserMovieRating.objects.count()
        if self.R is None or current != self.rating_count:
            self._build_matrix()

    # ==============================================================
    # SIMILARITY
    # ==============================================================

    def _cosine(
        self,
        u_idx: int,
        v_idx: int,
        selected_ids: Optional[List[int]] = None,
    ) -> float:
        """
        Base cosine similarity + boost when both users rated selected movies
        similarly (<=1.5 difference), stronger boost when <=0.5.
        Soft cap at +0.3 total.
        """
        a = self.R[u_idx, :]
        b = self.R[v_idx, :]

        mask = ~np.logical_or(np.isnan(a), np.isnan(b))
        if mask.sum() < 2:
            return 0.0

        a2 = a[mask]
        b2 = b[mask]

        denom = np.linalg.norm(a2) * np.linalg.norm(b2)
        if denom == 0:
            return 0.0

        base_sim = float(np.dot(a2, b2) / denom)

        # No boost if no selected movies
        if not selected_ids:
            return base_sim

        agreement_score = 0.0

        for mid in selected_ids:
            j = self.movie_index.get(mid)
            if j is None:
                continue

            ru = a[j]
            rv = b[j]
            if np.isnan(ru) or np.isnan(rv):
                continue

            diff = abs(float(ru) - float(rv))

            if diff <= 0.5:
                agreement_score += 2.0
            elif diff <= 1.5:
                agreement_score += 1.0

        if agreement_score > 0:
            boost = min(0.3, agreement_score * 0.05)
            return float(
                max(
                    0.0,
                    min(1.0, base_sim + boost)
                )
            )

        return base_sim

    def _neighbors(
        self,
        u_idx: int,
        selected_ids: Optional[List[int]] = None,
    ) -> List[Tuple[int, float]]:
        """
        Find k most similar neighbors for user u_idx.
        Similarity is optionally boosted based on agreement on selected_ids.
        """
        sims: List[Tuple[int, float]] = []

        for v_idx in range(self.R.shape[0]):
            if v_idx == u_idx:
                continue

            sim = self._cosine(u_idx, v_idx, selected_ids=selected_ids)
            if sim > 0:
                sims.append((v_idx, sim))

        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[: self.k_neighbors]

    # ==============================================================
    # PREDICTION
    # ==============================================================

    def predict_single(self, user_id: int, movie_id: int) -> Optional[float]:
        """
        Predict rating of `movie_id` for `user_id`.

        This helper is mainly for validation and does NOT use the
        "selected_ids" boosting (since it is typically called in isolation).
        """
        self._ensure_fresh()

        if user_id not in self.user_index or movie_id not in self.movie_index:
            return None

        u_idx = self.user_index[user_id]
        j = self.movie_index[movie_id]
        target = self.R[u_idx, :]

        was_rated = False
        if not np.isnan(target[j]):
            was_rated = True
            stored = target[j]
            self.R[u_idx, j] = np.nan

        user_mean = self.user_means[u_idx]
        neighbors = self._neighbors(u_idx, selected_ids=None)
        if not neighbors:
            if was_rated:
                self.R[u_idx, j] = stored
            return None

        num = 0.0
        den = 0.0

        for vidx, sim in neighbors:
            r = self.R[vidx, j]
            if np.isnan(r):
                continue
            num += sim * (r - self.user_means[vidx])
            den += abs(sim)

        if was_rated:
            self.R[u_idx, j] = stored

        if den > 0:
            return float(user_mean + num / den)
        else:
            return None
    
    @staticmethod
    def build_insight(neighbor_count: int, confidence: float, variance: Optional[float]):
        """
        Compact, human-friendly insight explaining
        WHY this movie was recommended.
        """

        # strongest
        if neighbor_count >= 5 and confidence >= 0.45 and (variance is not None and variance < 0.15):
            return {
                "badge": "🔥 Strong Match",
                "reason": "People with taste similar to yours consistently enjoyed this movie."
            }

        # decent
        if neighbor_count >= 3 and confidence >= 0.20:
            return {
                "badge": "👍 Good Match",
                "reason": "Viewers with similar preferences generally rated this movie well."
            }

        # fallback
        return {
            "badge": "🤔 Soft Suggestion",
            "reason": "This title was liked by a small number of viewers similar to you."
        }

    # ==============================================================
    # RECOMMEND
    # ==============================================================

    def _recommend_for_user(
        self,
        user_id: int,
        selected: List[int],
        top_k: int,
    ) -> List[dict]:
        """
        Recommend movies for the given user.
        `selected` is the list of currently selected movie IDs in the UI.

        We use `selected` in the neighbor-search step to boost neighbors
        who agree with the user on these specific movies.
        """
        self._ensure_fresh()

        if user_id not in self.user_index:
            raise ValueError("User lacks enough ratings to run CF.")

        u_idx = self.user_index[user_id]
        target_vec = self.R[u_idx, :]
        mean = self.user_means[u_idx]

        # Use boosted similarity that focuses more on selected movies
        neighbors = self._neighbors(u_idx, selected_ids=selected)
        if not neighbors:
            raise ValueError("CF could not find similar users.")

        preds = np.full(self.R.shape[1], np.nan)

        # Compute predictions
        for j in range(self.R.shape[1]):
            if not np.isnan(target_vec[j]):
                continue

            num = 0.0
            den = 0.0

            for v_idx, sim in neighbors:
                r = self.R[v_idx, j]
                if np.isnan(r):
                    continue

                num += sim * (r - self.user_means[v_idx])
                den += abs(sim)

            if den > 0:
                preds[j] = mean + num / den

        mask = ~np.isnan(preds)
        if mask.sum() == 0:
            raise ValueError("No predictions generated.")

        sorted_idx = np.argsort(preds[mask])[::-1]
        candidate_indices = np.where(mask)[0][sorted_idx]

        movie_ids = [self.movie_ids[i] for i in candidate_indices]
        # Do not recommend the already selected movies
        movie_ids = [m for m in movie_ids if m not in selected]
        movie_ids = movie_ids[: top_k]

        movies = Movie.objects.filter(id__in=movie_ids).values("id", "title", "genres", "year")
        byid = {m["id"]: m for m in movies}

        results = []
        max_rating = 5.0

        for mid in movie_ids:
            if mid not in byid:
                continue

            raw_pred = float(preds[self.movie_index[mid]])

            # ----- Build trust metrics -----
            sims_used = []
            neighbor_ratings = []

            for vidx, sim in neighbors:
                r = self.R[vidx, self.movie_index[mid]]
                if np.isnan(r):
                    continue
                sims_used.append(sim)
                neighbor_ratings.append(r)

            neighbor_count = len(neighbor_ratings)
            variance = float(np.var(neighbor_ratings)) if neighbor_ratings else None
            total_sim = float(sum(sims_used))

            # Normalize confidence
            confidence = min(1.0, total_sim / 15.0)

            if confidence >= 0.8 and (variance is not None and variance < 0.12):
                category = "High"
            elif confidence >= 0.6:
                category = "Medium"
            else:
                category = "Low"

            insight = self.build_insight(neighbor_count, confidence, variance)
            print(byid[mid])
            results.append(
                {
                    "id": mid,
                    "title": byid[mid]["title"],
                    "year": byid[mid].get("year"),
                    "genres": byid[mid].get("genres", "") or "",
                    "predicted_rating": round(raw_pred, 2),
                    "badge": insight["badge"],
                    "reason": insight["reason"],
                    "score": max(0.0, min(1.0, raw_pred / max_rating)),
                }
            )

        return results

    def recommend(self, user: User, selected_movie_ids: List[int], top_k: int = 16) -> List[dict]:
        """
        Public entry point: recommend for a given Django user + currently
        selected movies.
        """
        return self._recommend_for_user(user.id, selected_movie_ids, top_k)


# ==============================================================
# GLOBAL INSTANCE
# ==============================================================

_cf_engine: Optional[DjangoCollaborativeFiltering] = None


def get_cf_engine() -> DjangoCollaborativeFiltering:
    global _cf_engine
    if _cf_engine is None:
        _cf_engine = DjangoCollaborativeFiltering()
    return _cf_engine


def recommend_collaborative(
    selected_ids: List[int],
    top_k: int = 16,
    user: Optional[User] = None,
) -> List[dict]:
    """
    Helper function used by the API layer.

    - Requires an authenticated user.
    - Uses ratings stored in UserMovieRating.
    - Gives extra weight to ratings on the currently selected movies.
    """
    if user is None or not user.is_authenticated:
        raise ValueError("Collaborative filtering requires an authenticated user.")

    return get_cf_engine().recommend(user, selected_ids, top_k)
