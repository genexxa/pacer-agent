from flask import Flask, request, jsonify
import os
import requests
import openai
import json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
STRAVA_BACKEND_URL = "https://pacerai-strava.onrender.com"

def get_strava_activities(strava_id):
    """Calls your backend to get Strava activity data"""
    url = f"{STRAVA_BACKEND_URL}/activities?strava_id={strava_id}"
    response = requests.get(url)
    return response.json()

def run_gpt_analysis(strava_id, activities_data):
    messages = [
        {
            "role": "system",
            "content": "You are Pacer, an expert ultrarunning coach. Analyze Strava data and give personalized, clear, and motivational feedback."
        },
        {
            "role": "user",
            "content": f"My Strava ID is {strava_id}. What have I done this week?"
        },
        {
            "role": "function",
            "name": "get_strava_activities",
            "content": json.dumps(activities_data)
        }
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4-0613",
        messages=messages
    )

    return response.choices[0].message["content"]

@app.route("/coach")
def coach():
    strava_id = request.args.get("strava_id")
    if not strava_id:
        return jsonify({"error": "Missing strava_id parameter"}), 400

    activities = get_strava_activities(strava_id)
    if not activities or "activities" not in activities:
        return jsonify({"error": "Could not retrieve Strava data"}), 500

    feedback = run_gpt_analysis(strava_id, activities)
    return jsonify({"feedback": feedback})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
