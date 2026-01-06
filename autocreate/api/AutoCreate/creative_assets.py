# creative_assets.py
import os
import base64
import uuid
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify
from runwayml import RunwayML, TaskFailedError

# --------------------------------------------------
# Blueprint
# --------------------------------------------------

creative_assets_bp = Blueprint("creative_assets", __name__)

# --------------------------------------------------
# Runway Client
# --------------------------------------------------

RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
client = RunwayML(api_key=RUNWAY_API_KEY) if RUNWAY_API_KEY else None

# --------------------------------------------------
# In-memory storage (replace with DB later)
# --------------------------------------------------

campaigns = {}
user_uploads = {}

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def get_mime_type(filename):
    ext = filename.lower().split(".")[-1]
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp"
    }.get(ext, "image/png")


def generate_image_with_runway(image_b64, prompt, filename):
    if not client:
        raise RuntimeError("RUNWAY_API_KEY not configured")

    mime = get_mime_type(filename)
    data_uri = f"data:{mime};base64,{image_b64}"

    task = client.text_to_image.create(
        model="gen4_image_turbo",
        ratio="1080:1080",
        prompt_text=prompt,
        reference_images=[{"uri": data_uri, "tag": "product"}],
    )

    result = task.wait_for_task_output()

    if not result or not result.output:
        raise RuntimeError("Runway returned no output")

    return {
        "image_url": result.output[0],
        "task_id": task.id
    }

# --------------------------------------------------
# Routes
# --------------------------------------------------

@creative_assets_bp.route("/api/upload-image", methods=["POST", "OPTIONS"])
def upload_image():
    data = request.get_json()
    user_id = data.get("user_id")
    image_data = data.get("image_data")
    filename = data.get("filename", "image.png")
    campaign_id = data.get("campaign_id") or f"campaign_{uuid.uuid4().hex[:8]}"
    ad_type = data.get("ad_type", "")

    if not user_id or not image_data:
        return jsonify({"error": "Missing user_id or image_data"}), 400

    user_uploads.setdefault(user_id, {})[campaign_id] = {
        "image_data": image_data,
        "filename": filename,
        "ad_type": ad_type,
        "uploaded_at": datetime.utcnow().isoformat()
    }

    campaigns.setdefault(campaign_id, {
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "assets": []
    })

    return jsonify({
        "success": True,
        "campaign_id": campaign_id
    }), 200


@creative_assets_bp.route("/api/generate-assets", methods=["POST", "OPTIONS"])
def generate_assets():
    data = request.get_json()
    user_id = data.get("user_id")
    campaign_id = data.get("campaign_id")
    campaign_goal = data.get("campaign_goal", "awareness")
    ad_type = data.get("ad_type")

    if not user_id or not campaign_id:
        return jsonify({"error": "Missing user_id or campaign_id"}), 400

    upload = user_uploads.get(user_id, {}).get(campaign_id)
    if not upload:
        return jsonify({"error": "No uploaded image found"}), 400

    if not ad_type:
        return jsonify({"error": "ad_type is required"}), 400

    goal_prompts = {
        "awareness": "eye-catching brand awareness advertisement",
        "consideration": "engaging product showcase",
        "conversions": "conversion-focused advertisement",
        "retention": "customer retention advertisement"
    }

    base_prompt = goal_prompts.get(campaign_goal, "professional product advertisement")

    prompts = [
        f"@product in {ad_type}, {base_prompt}, studio lighting, commercial photography",
        f"@product in {ad_type}, lifestyle setting, natural lighting, modern aesthetic",
        f"@product in {ad_type}, minimalist design, bold colors, marketing focused",
        f"@product in {ad_type}, creative concept, premium quality",
        f"@product in {ad_type}, social media optimized, vibrant colors"
    ]

    assets = []

    for i, prompt in enumerate(prompts):
        try:
            result = generate_image_with_runway(
                upload["image_data"],
                prompt,
                upload["filename"]
            )
            assets.append({
                "id": i + 1,
                "title": f"{ad_type} – Variation {i + 1}",
                "image_url": result["image_url"],
                "prompt": prompt,
                "score": 85 + i * 2,
                "task_id": result["task_id"]
            })
        except Exception as e:
            print(f"Generation failed: {e}")

    if not assets:
        return jsonify({"error": "Failed to generate assets"}), 500

    campaigns[campaign_id]["assets"] = assets

    return jsonify({
        "success": True,
        "campaign_id": campaign_id,
        "assets": assets
    }), 200


@creative_assets_bp.route("/api/save-selected-assets", methods=["POST","OPTIONS"])
def save_selected_assets():
    data = request.get_json()
    campaign_id = data.get("campaign_id")
    selected_assets = data.get("selected_assets", [])

    if campaign_id not in campaigns:
        return jsonify({"error": "Campaign not found"}), 404

    campaigns[campaign_id]["selected_assets"] = selected_assets
    campaigns[campaign_id]["updated_at"] = datetime.utcnow().isoformat()

    return jsonify({
        "success": True,
        "saved": len(selected_assets)
    }), 200


@creative_assets_bp.route("/api/create-campaign", methods=["POST", "OPTIONS"])
def create_campaign():
    data = request.get_json()
    user_id = data.get("user_id")
    goal = data.get("campaign_goal", "awareness")

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
    campaigns[campaign_id] = {
        "user_id": user_id,
        "campaign_goal": goal,
        "created_at": datetime.utcnow().isoformat(),
        "assets": []
    }

    return jsonify({
        "success": True,
        "campaign_id": campaign_id
    }), 200


@creative_assets_bp.route("/api/creative/health", methods=["GET", "OPTIONS"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "creative-assets",
        "runway_configured": bool(client)
    }), 200
