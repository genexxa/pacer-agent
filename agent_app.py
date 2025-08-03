from flask import Flask, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
import requests

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load Strava API credentials from environment
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = "https://pacer-agent.onrender.com/callback"

# Database model
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

# Routes
@app.route("/")
def index():
    return "✅ Pacer Agent is live. Use /auth to connect your Strava account."

@app.route("/auth")
def auth():
    url = (
        f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
        f"&response_type=code&redirect_uri={REDIRECT_URI}"
        f"&scope=activity:read_all&approval_prompt=force"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "❌ No code received", 400

    resp = requests.post("https://www.strava.com/oauth/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    })

    if resp.status_code != 200:
        return f"❌ Token exchange failed: {resp.text}", 400

    data = resp.json()
    athlete = data["athlete"]
    expires_at = datetime.utcfromtimestamp(data["expires_at"])

    user = User.query.filter_by(strava_id=athlete["id"]).first()
    if not user:
        user = User(
            strava_id=athlete["id"],
            firstname=athlete.get("firstname", ""),
            lastname=athlete.get("lastname", ""),
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_expires_at=expires_at
        )
        db.session.add(user)
    else:
        user.access_token = data["access_token"]
        user.refresh_token = data["refresh_token"]
        user.token_expires_at = expires_at

    db.session.commit()
    return f"✅ Strava account linked for {athlete['firstname']}"

@app.route("/users")
def list_users():
    users = User.query.all()
    return jsonify({
        "users": [{
            "id": u.id,
            "strava_id": u.strava_id,
            "firstname": u.firstname,
            "lastname": u.lastname,
            "token_expires_at": u.token_expires_at.isoformat()
        } for u in users]
    })

@app.route("/coach", methods=["GET"])
def coach():
    strava_id = request.args.get("strava_id")
    if not strava_id:
        return jsonify({"error": "Missing strava_id query parameter"}), 400

    user = User.query.filter_by(strava_id=int(strava_id)).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # ✅ Only return a short text feedback here
    feedback = (
        f"Hi {user.firstname}, you're doing great! Your training looks consistent. "
        "Let’s continue to build aerobic endurance and include a longer run this week."
    )

    return jsonify({"feedback": feedback})


@app.route("/activities")
def activities():
    strava_id = request.args.get("strava_id")
    if not strava_id:
        return jsonify({"error": "Missing strava_id query parameter"}), 400

    user = User.query.filter_by(strava_id=int(strava_id)).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.token_expires_at < datetime.utcnow():
        refresh = requests.post("https://www.strava.com/oauth/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": user.refresh_token
        })

        if refresh.status_code != 200:
            return jsonify({"error": "Token refresh failed"}), 400

        data = refresh.json()
        user.access_token = data["access_token"]
        user.refresh_token = data["refresh_token"]
        user.token_expires_at = datetime.utcfromtimestamp(data["expires_at"])
        db.session.commit()

    headers = {"Authorization": f"Bearer {user.access_token}"}
    response = requests.get("https://www.strava.com/api/v3/athlete/activities", headers=headers, params={"per_page": 5})

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch activities"}), 400

    return jsonify({
        "activities": [{
            "name": act["name"],
            "distance_km": round(act["distance"] / 1000, 2),
            "duration_min": round(act["moving_time"] / 60, 1),
            "type": act["type"],
            "start": act["start_date"]
        } for act in response.json()]
    })

# Start app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
