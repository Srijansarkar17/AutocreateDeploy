import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from runwayml import RunwayML

creative_assets_bp = Blueprint("creative_assets", __name__)

RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
client = RunwayML(api_key=RUNWAY_API_KEY) if RUNWAY_API_KEY else None


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
# STATELESS GENERATION (Railway-safe)
# --------------------------------------------------
@creative_assets_bp.route("/api/generate-assets", methods=["POST", "OPTIONS"])
def generate_assets():
    data = request.get_json()

    image_data = data.get("image_data")
    filename = data.get("filename", "image.png")
    campaign_goal = data.get("campaign_goal", "awareness")
    ad_type = data.get("ad_type")

    if not image_data:
        return jsonify({"error": "image_data is required"}), 400

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
                image_data,
                prompt,
                filename
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
            print("Generation failed:", e)

    if not assets:
        return jsonify({"error": "Failed to generate assets"}), 500

    return jsonify({
        "success": True,
        "assets": assets
    }), 200


@creative_assets_bp.route("/api/creative/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "creative-assets",
        "runway_configured": bool(client)
    }), 200
