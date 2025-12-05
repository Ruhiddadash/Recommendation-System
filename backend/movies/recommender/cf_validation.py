import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from movies.models import UserMovieRating
from .collabfiltering import DjangoCollaborativeFiltering


def validate_cf(test_ratio: float = 0.2, k_neighbors: int = 50):
    """
    Validate the CF model with RMSE and MAE on a hold-out test set.
    """
    
    qs = UserMovieRating.objects.values("user_id", "movie_id", "rating")
    df = pd.DataFrame.from_records(qs)
    if df.empty:
        raise ValueError("No ratings in DB — cannot validate.")

    # Train/Test split
    train_df, test_df = train_test_split(df, test_size=test_ratio, random_state=42)

    # Inject train-only data into CF engine
    engine = DjangoCollaborativeFiltering(k_neighbors=k_neighbors)
    engine._build_matrix_from_df(train_df)

    y_true = []
    y_pred = []

    for row in test_df.itertuples():
        
        user = int(row.user_id)
        movie = int(row.movie_id)
        true_rating = float(row.rating)
        #print(true_rating)

        # Only test if user is known in train set AND movie in matrix
        if user not in engine.user_index or movie not in engine.movie_index:
            continue

        try:
            pred = engine.predict_single(user_id=user, movie_id=movie)
            #print("pred: ", pred)
        except Exception:
            continue

        if pred is not None:
            y_true.append(true_rating)
            y_pred.append(pred)

    if not y_true:
        #print("y_true: ", y_true)
        raise ValueError("No overlapping data to validate CF.")

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    rmse = np.sqrt(np.mean((y_true - y_pred)**2))
    mae = np.mean(np.abs(y_true - y_pred))

    return {
        "total_tested": len(y_true),
        "rmse": float(rmse),
        "mae": float(mae)
    }
