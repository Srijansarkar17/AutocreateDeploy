# budget_testing.py
from flask import Blueprint, request, jsonify
import os
from dotenv import load_dotenv
import jwt

from autocreate.unified_db import (
    decode_jwt_token,
    handle_campaign_save,
    get_active_campaign
)

# Supabase
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

load_dotenv()

budget_testing_bp = Blueprint("budget_testing", __name__)

# --------------------------------------------------
# Supabase setup
# --------------------------------------------------

if SUPABASE_AVAILABLE and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
else:
    class MockSupabase:
        def table(self, _): return self
        def select(self, *_): return self
        def update(self, *_): return self
        def eq(self, *_): return self
        def execute(self):
            return type("obj", (), {"data": [{"id": 1}]})
    supabase = MockSupabase()

# --------------------------------------------------
# Routes
# --------------------------------------------------

@budget_testing_bp.route("/api/budget-testing/save", methods=["POST"])
def save_budget_testing():
    try:
        data = request.get_json()

        token = data.get("user_id")
        if not token:
            return jsonify({"error": "Missing auth token"}), 401

        user_id = decode_jwt_token(token)

        budget_type = data["budget_type"]
        budget_amount = float(data["budget_amount"])
        campaign_duration = int(data["campaign_duration"])
        selected_tests = data["selected_tests"]

        budget_data = {
            "budget_type": budget_type,
            "budget_amount": budget_amount,
            "campaign_duration": campaign_duration,
            "selected_tests": selected_tests,
            "messaging_tone": data.get("messaging_tone")
        }

        campaign_id = data.get("campaign_id")

        save_result = handle_campaign_save(
            supabase,
            user_id,
            budget_data,
            campaign_id
        )

        if not save_result["success"]:
            return jsonify({"error": save_result["error"]}), 500

        campaign_result = get_active_campaign(
            supabase,
            user_id,
            save_result["campaign_id"]
        )

        projections = calculate_projections(
            budget_type,
            budget_amount,
            campaign_duration,
            selected_tests,
            campaign_result["campaign"].get("campaign_goal")
        )

        return jsonify({
            "success": True,
            "campaign_id": save_result["campaign_id"],
            "projections": projections
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@budget_testing_bp.route("/api/budget-testing/<campaign_id>", methods=["GET"])
def get_budget_testing(campaign_id):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = decode_jwt_token(token)

    response = supabase.table("auto_create") \
        .select("*") \
        .eq("id", int(campaign_id)) \
        .eq("user_id", user_id) \
        .execute()

    if not response.data:
        return jsonify({"error": "Campaign not found"}), 404

    return jsonify(response.data[0]), 200


@budget_testing_bp.route("/api/budget-testing/projections", methods=["POST"])
def get_projections():
    data = request.get_json()

    projections = calculate_projections(
        data.get("budget_type", "daily"),
        float(data.get("budget_amount", 500)),
        int(data.get("campaign_duration", 14)),
        data.get("selected_tests", []),
        data.get("campaign_goal")
    )

    return jsonify({"success": True, "projections": projections}), 200


@budget_testing_bp.route("/api/budget-testing/testing-options", methods=["GET"])
def get_testing_options():
    return jsonify({
        "testing_options": [
            {"id": "creative", "variants": 3},
            {"id": "audience", "variants": 2},
            {"id": "messaging", "variants": 4}
        ]
    }), 200


@budget_testing_bp.route("/api/budget-testing/budget-recommendations", methods=["GET"])
def budget_recommendations():
    goal = request.args.get("goal", "consideration")

    return jsonify({
        "goal": goal,
        "recommended_budget": "$500 - $2000"
    }), 200


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def calculate_total_budget(budget_type, budget_amount, duration):
    return budget_amount * duration if budget_type == "daily" else budget_amount


def calculate_projections(budget_type, budget_amount, duration, tests, goal=None):
    daily_spend = budget_amount if budget_type == "daily" else budget_amount / duration
    return {
        "daily_spend": daily_spend,
        "expected_roas": "3.2x - 4.8x",
        "tests_running": len(tests)
    }
