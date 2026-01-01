# copy_messaging.py
import os
import json
import uuid
import jwt
import logging
from flask import Blueprint, request, jsonify
from groq import Groq
from supabase import create_client, Client
from dotenv import load_dotenv

from autocreate.unified_db import (
    decode_jwt_token,
    handle_campaign_save,
    get_active_campaign
)

load_dotenv()

# --------------------------------------------------
# Logging
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# Blueprint
# --------------------------------------------------

copy_messaging_bp = Blueprint("copy_messaging", __name__)

# --------------------------------------------------
# Environment
# --------------------------------------------------

JWT_SECRET = os.getenv("SECRET_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# --------------------------------------------------
# Clients
# --------------------------------------------------

groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

supabase: Client | None = (
    create_client(SUPABASE_URL, SUPABASE_KEY)
    if SUPABASE_URL and SUPABASE_KEY
    else None
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def decode_user_id_from_token(token: str):
    try:
        try:
            return str(uuid.UUID(token))
        except ValueError:
            pass

        if token.startswith("Bearer "):
            token = token[7:]

        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded.get("user_id")

    except Exception as e:
        logger.error(f"JWT decode failed: {e}")
        return None


def generate_copy_with_groq(message: str, tone: str):
    system_prompt = f"""
    You are an expert copywriter.
    Generate 3 ad copy variations in {tone} tone.
    Return ONLY valid JSON.
    """

    chat = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        temperature=0.7,
        max_tokens=1200,
    )

    content = chat.choices[0].message.content
    start, end = content.find("{"), content.rfind("}") + 1
    return json.loads(content[start:end])


def analyze_copy(selected_copy: dict):
    prompt = f"""
    Analyze this marketing copy and return JSON insights.

    Headline: {selected_copy.get("headline")}
    Body: {selected_copy.get("body")}
    CTA: {selected_copy.get("cta")}
    """

    chat = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=800,
    )

    content = chat.choices[0].message.content
    start, end = content.find("{"), content.rfind("}") + 1
    return json.loads(content[start:end])

# --------------------------------------------------
# Routes
# --------------------------------------------------

@copy_messaging_bp.route("/api/generate-copy", methods=["POST"])
def generate_copy():
    data = request.get_json()

    message = data.get("message")
    tone = data.get("tone", "energetic")
    token = data.get("user_id")
    campaign_id = data.get("campaign_id", str(uuid.uuid4()))

    if not message or not token:
        return jsonify({"error": "Missing message or user token"}), 400

    user_id = decode_user_id_from_token(token)
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401

    copy_data = generate_copy_with_groq(message, tone)
    copy_data["campaign_id"] = campaign_id

    return jsonify({
        "success": True,
        "data": copy_data
    }), 200


@copy_messaging_bp.route("/api/analyze-copy", methods=["POST"])
def analyze_copy_route():
    data = request.get_json()

    selected_copy = data.get("selected_copy")
    token = data.get("user_id")

    if not selected_copy or not token:
        return jsonify({"error": "Missing data"}), 400

    user_id = decode_user_id_from_token(token)
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401

    analysis = analyze_copy(selected_copy)

    return jsonify({
        "success": True,
        "data": analysis
    }), 200


@copy_messaging_bp.route("/api/save-campaign", methods=["POST"])
def save_campaign():
    data = request.get_json()

    token = data.get("user_id")
    campaign_id = data.get("campaign_id")
    messaging_tone = data.get("messaging_tone")
    post_caption = data.get("post_caption")

    if not all([token, campaign_id, messaging_tone, post_caption]):
        return jsonify({"error": "Missing fields"}), 400

    user_id = decode_jwt_token(token)

    caption_text = (
        f"{post_caption.get('headline','')}\n\n"
        f"{post_caption.get('body','')}\n\n"
        f"{post_caption.get('cta','')}"
    )

    save_result = handle_campaign_save(
        supabase,
        user_id,
        {
            "messaging_tone": messaging_tone,
            "post_caption": caption_text
        },
        campaign_id
    )

    if not save_result["success"]:
        return jsonify({"error": save_result["error"]}), 500

    return jsonify({
        "success": True,
        "campaign_id": save_result["campaign_id"]
    }), 200


@copy_messaging_bp.route("/api/copy/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "copy-messaging",
        "groq": bool(GROQ_API_KEY),
        "supabase": bool(supabase)
    }), 200
