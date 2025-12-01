from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import Session
from models import Movie, UserMovieSelection
from database import SessionLocal

# Recommenders
from recommender.contentbase import get_similar_movies_by_titles
from recommender.collabfiltering_vol2 import CollaborativeFiltering

movie_bp = Blueprint("movies", __name__)

# CF engine global load (dataset çok büyük, tekrar yüklemeyelim!)
cf_engine = CollaborativeFiltering()
cf_engine.load_movielens_data(dataset='1m', sample_users=1000)


@movie_bp.route("/movies", methods=["GET"])
def all_movies():
    db: Session = SessionLocal()
    movies = db.query(Movie).all()
    return jsonify([{
        "id": m.id,
        "title": m.title,
        "genre": m.genre,
        "rating": m.rating,
    } for m in movies])


@movie_bp.route("/select", methods=["POST"])
@jwt_required()
def save_selection():
    user_id = get_jwt_identity()
    data = request.json

    titles = data.get("movies", [])

    db: Session = SessionLocal()
    for t in titles:
        sel = UserMovieSelection(user_id=user_id, movie_title=t)
        db.add(sel)
    db.commit()

    return jsonify({"message": "Movies saved!"})


@movie_bp.route("/recommend", methods=["POST"])
@jwt_required()
def recommend_movies():
    data = request.json
    selected_titles = data.get("movies", [])
    algorithm = data.get("algorithm", "hybrid")

    if len(selected_titles) == 0:
        return jsonify({"error": "No movies provided"}), 400

    # Content based result
    content_results = get_similar_movies_by_titles(selected_titles, n=10)

    # Collaborative filtering result - fake user id by token
    user_id = get_jwt_identity()
    collab_results = []
    try:
        collab = cf_engine.user_based_cf(user_id, top_n=10)
        collab_results = [c["title"] for c in collab]
    except:
        collab_results = []

    # Hybrid
    final_results = []

    if algorithm == "content_based":
        final_results = content_results

    elif algorithm == "collaborative":
        final_results = collab_results

    else:  # hybrid
        merged = list(dict.fromkeys(content_results + collab_results))
        final_results = merged[:10]

    return jsonify({
        "success": True,
        "algorithm": algorithm,
        "recommendations": final_results
    })
