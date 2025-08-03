from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
import requests


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
@app.route("/coach", methods=["GET"])
def coach():
    strava_id = request.args.get("strava_id")
    if not strava_id:
        return jsonify({"error": "Missing strava_id query parameter"}), 400

    user = User.query.filter_by(strava_id=int(strava_id)).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "feedback": f"Great work, {user.firstname}! Based on your recent activity, you're staying consistent. Keep it up!"
    })

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
# Ensure DB tables exist (executed once at startup)
with app.app_context():
    db.create_all()

from datetime import datetime, timedelta
from flask import jsonify

@app.route("/activities", methods=["GET"])
def get_recent_activities():
    strava_id = request.args.get("strava_id")
    if not strava_id:
        return jsonify({"error": "Missing strava_id query parameter"}), 400

    user = User.query.filter_by(strava_id=strava_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Refresh token if expired
    if user.token_expires_at < datetime.utcnow():
        refresh_resp = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": user.refresh_token
        })

        if refresh_resp.status_code != 200:
            return jsonify({"error": "Token refresh failed"}), 400

        refresh_data = refresh_resp.json()
        user.access_token = refresh_data['access_token']
        user.refresh_token = refresh_data['refresh_token']
        user.token_expires_at = datetime.utcfromtimestamp(refresh_data['expires_at'])
        db.session.commit()

    # Call Strava API
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {user.access_token}"}
    resp = requests.get(activities_url, headers=headers, params={"per_page": 5})

    if resp.status_code != 200:
        return jsonify({"error": "Failed to fetch activities"}), 400

    data = resp.json()

    # Return simplified activity info
    recent = [{
        "name": a["name"],
        "distance_km": round(a["distance"] / 1000, 2),
        "moving_time_min": round(a["moving_time"] / 60, 1),
        "type": a["type"],
        "start_date": a["start_date"]
    } for a in data]

    return jsonify({"activities": recent})
