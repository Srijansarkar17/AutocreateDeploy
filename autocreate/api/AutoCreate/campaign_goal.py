# campaign_goal.py
"""
Campaign Goal Service (Blueprint version – Railway compatible)
"""

import os
import jwt
import traceback
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

campaign_goal_bp = Blueprint("campaign_goal", __name__)

# --------------------------------------------------
# Environment & Supabase
# --------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")

supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def decode_jwt_token(token: str) -> str:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("user_id missing in token")
    return str(user_id)


def save_campaign_goal(user_id: str, goal: str, campaign_id: str | None):
    if not supabase:
        return None, "Supabase not configured"

    try:
        if campaign_id:
            res = (
                supabase.table("auto_create")
                .update({"campaign_goal": goal})
                .eq("id", int(campaign_id))
                .eq("user_id", user_id)
                .execute()
            )
            if not res.data:
                return None, "Campaign not found or access denied"
            return campaign_id, None

        res = supabase.table("auto_create").insert({
            "user_id": user_id,
            "campaign_goal": goal,
            "campaign_status": "draft",
            "budget_amount": 0,
            "campaign_duration": 30
        }).execute()

        if not res.data:
            return None, "Failed to create campaign"

        return str(res.data[0]["id"]), None

    except Exception as e:
        print(traceback.format_exc())
        return None, str(e)

# --------------------------------------------------
# Routes
# --------------------------------------------------

@campaign_goal_bp.route("/api/campaign-goal", methods=["POST"])
def create_campaign_goal():
    try:
        data = request.get_json()

        goal = data.get("goal")
        token = data.get("user_id")
        campaign_id = data.get("campaign_id")

        if not goal or not token:
            return jsonify({"error": "Missing goal or auth token"}), 400

        if goal not in ["awareness", "consideration", "conversions", "retention"]:
            return jsonify({"error": "Invalid campaign goal"}), 400

        user_id = decode_jwt_token(token)

        campaign_id, err = save_campaign_goal(user_id, goal, campaign_id)
        if err:
            return jsonify({"error": err}), 500

        return jsonify({
            "success": True,
            "campaign_id": campaign_id,
            "campaign_goal": goal
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@campaign_goal_bp.route("/api/campaign-goal/<campaign_id>", methods=["PUT"])
def update_campaign_goal(campaign_id):
    try:
        data = request.get_json()
        goal = data.get("goal")
        token = data.get("user_id")

        if not goal or not token:
            return jsonify({"error": "Missing goal or auth token"}), 400

        user_id = decode_jwt_token(token)

        campaign_id, err = save_campaign_goal(user_id, goal, campaign_id)
        if err:
            return jsonify({"error": err}), 500

        return jsonify({
            "success": True,
            "campaign_id": campaign_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@campaign_goal_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "campaign-goal",
        "supabase": bool(supabase)
    }), 200
