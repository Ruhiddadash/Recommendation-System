from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from database import engine, Base
from auth_routes import auth
from movie_routes import movie_bp

app = Flask(__name__)
CORS(app)

app.config["JWT_SECRET_KEY"] = "SUPER_SECRET_KEY"
jwt = JWTManager(app)

# create tables
Base.metadata.create_all(bind=engine)

# routes
app.register_blueprint(auth, url_prefix="/api/auth")
app.register_blueprint(movie_bp, url_prefix="/api")

@app.route("/")
def home():
    return "Movie Recommendation Backend is running!"

if __name__ == "__main__":
    app.run(port=5000, debug=True)
