from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from models import User
from database import SessionLocal
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token

auth = Blueprint("auth", __name__)
bcrypt = Bcrypt()

@auth.route("/register", methods=["POST"])
def register():
    data = request.json
    db: Session = SessionLocal()

    if db.query(User).filter(User.email == data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(
        name=data["name"],
        email=data["email"],
        password=hashed_pw
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return jsonify({"message": "User created"}), 201


@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    db: Session = SessionLocal()

    user = db.query(User).filter(User.email == data["email"]).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=user.id)

    return jsonify({
        "message": "Login success",
        "token": token,
        "user": {"id": user.id, "name": user.name, "email": user.email}
    })
