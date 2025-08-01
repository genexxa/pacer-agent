from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# PostgreSQL config (Render sets DATABASE_URL automatically)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.Integer, unique=True, nullable=False)
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    access_token = db.Column(db.String(255))
