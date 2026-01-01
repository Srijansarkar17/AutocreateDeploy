# audience_step.py
from flask import Blueprint, request, jsonify
import os
import jwt
import traceback
from dotenv import load_dotenv

# Try to import supabase
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠ Supabase not installed. Using mock client.")

load_dotenv()

# --------------------------------------------------
# Blueprint
# --------------------------------------------------

audience_bp = Blueprint("audience", __name__)

# --------------------------------------------------
# JWT Config
# --------------------------------------------------

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")

# --------------------------------------------------
# Supabase setup
# --------------------------------------------------

if SUPABASE_AVAILABLE and os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
else:
    # Mock Supabase (dev fallback)
    class MockSupabase:
        def table(self, _):
            return self

        def select(self, *_): return self
        def insert(self, *_): return self
        def update(self, *_): return self
        def eq(self, *_): return self

        def execute(self):
            return type("obj", (), {
                "data": [{
                    "id": 1,
                    "demographics": ["male", "female"],
                    "age_range_min": 25,
                    "age_range_max": 45,
                    "selected_interests": [{"id": "fitness"}],
                    "target_locations": [{"name": "India"}],
                    "campaign_status": "draft"
                }]
            })

    supabase = MockSupabase()

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def decode_jwt_token(token: str) -> str:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("user_id missing in token")
    return str(user_id)

# --------------------------------------------------
# Routes
# --------------------------------------------------

@audience_bp.route("/api/audience/targeting", methods=["POST"])
def save_audience_targeting():
    try:
        data = request.get_json()

        token = data.get("user_id")
        if not token:
            return jsonify({"error": "Missing auth token"}), 401

        user_id = decode_jwt_token(token)

        audience_data = {
            "demographics": data["demographics"],
            "age_range_min": data["age_range_min"],
            "age_range_max": data["age_range_max"],
            "selected_interests": data["selected_interests"],
            "target_locations": data["target_locations"]
        }

        campaign_id = data.get("campaign_id")

        if campaign_id:
            response = supabase.table("auto_create") \
                .update(audience_data) \
                .eq("id", int(campaign_id)) \
                .eq("user_id", user_id) \
                .execute()
        else:
            response = supabase.table("auto_create") \
                .insert({
                    "user_id": user_id,
                    "campaign_status": "draft",
                    **audience_data
                }) \
                .execute()

        if not response.data:
            return jsonify({"error": "Database operation failed"}), 500

        return jsonify({
            "success": True,
            "campaign_id": response.data[0]["id"]
        }), 200

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@audience_bp.route("/api/audience/targeting/<campaign_id>", methods=["GET"])
def get_audience_targeting(campaign_id):
    try:
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@audience_bp.route("/api/audience/insights", methods=["POST"])
def get_audience_insights():
    data = request.get_json()

    age_min = data.get("age_range_min", 25)
    age_max = data.get("age_range_max", 45)
    interests = data.get("selected_interests", [])

    estimated_audience = int(
        1_000_000 * (0.6 + len(interests) * 0.1)
    )

    return jsonify({
        "success": True,
        "insights": {
            "estimated_audience": f"{estimated_audience:,}",
            "average_age": (age_min + age_max) // 2,
            "recommendations": [
                "Test multiple creatives",
                "Optimize for mobile",
                "Refine interests"
            ]
        }
    }), 200


@audience_bp.route("/api/audience/preset-interests", methods=["GET"])
def preset_interests():
    return jsonify({
        "interests": [
            {"id": "fitness", "label": "Fitness"},
            {"id": "sports", "label": "Sports"},
            {"id": "fashion", "label": "Fashion"},
            {"id": "technology", "label": "Technology"}
        ]
    }), 200


@audience_bp.route("/api/audience/preset-locations", methods=["GET"])
def preset_locations():
    return jsonify({
        "locations": [
            {"code": "IN", "name": "India"},
            {"code": "US", "name": "United States"},
            {"code": "UK", "name": "United Kingdom"}
        ]
    }), 200
