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
    refresh_token = db.Column(db.String(255))
    token_expires_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<User {self.strava_id} - {self.firstname}>"

# Root route to confirm service is up
@app.route("/")
def index():
    return "✅ Pacer Agent is running. Try /coach?strava_id=XXXX"

# Coaching route for GPT integration
@app.route("/coach")
def coach():
    strava_id = request.args.get("strava_id", type=int)
    if not strava_id:
        return jsonify({"error": "❌ Missing strava_id"}), 400

    user = User.query.filter_by(strava_id=strava_id).first()
    if not user:
        return jsonify({"error": "❌ User not found"}), 404

    feedback = (
        f"Great work, {user.firstname}! Based on your recent activity, "
        "you're staying consistent. Keep up the strong training!"
    )

    return jsonify({"feedback": feedback})

# Ensure DB tables exist (executed once at startup)
with app.app_context():
    db.create_all()
