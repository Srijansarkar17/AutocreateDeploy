import os
from flask import Blueprint, request, jsonify
from runwayml import RunwayML

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
# Helpers
# --------------------------------------------------
def get_mime_type(filename: str) -> str:
    ext = filename.lower().split(".")[-1]
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp"
    }.get(ext, "image/png")


def start_runway_generation(image_b64: str, prompt: str, filename: str):
    """
    Starts Runway generation WITHOUT blocking.
    Returns task_id immediately (PRODUCTION SAFE).
    """
    if not client:
        raise RuntimeError("RUNWAY_API_KEY not configured")

    mime = get_mime_type(filename)
    data_uri = f"data:{mime};base64,{image_b64}"

    task = client.text_to_image.create(
        model="gen4_image_turbo",
        ratio="1080:1080",
        prompt_text=prompt,
        reference_images=[
            {
                "uri": data_uri,
                "tag": "product"
            }
        ],
    )

    return {
        "task_id": task.id,
        "status": task.status
    }

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@creative_assets_bp.route("/api/generate-assets", methods=["POST", "OPTIONS"])
def generate_assets():
    """
    Starts image generation and returns task_id.
    DOES NOT WAIT FOR RESULT (Gunicorn-safe).
    """
    try:
        if request.method == "OPTIONS":
            return jsonify({"ok": True}), 200

        data = request.get_json(force=True)

        image_data = data.get("image_data")
        filename = data.get("filename", "image.png")
        campaign_goal = data.get("campaign_goal", "awareness")
        ad_type = data.get("ad_type")

        if not image_data:
            return jsonify({"error": "image_data is required"}), 400

        if not ad_type:
            return jsonify({"error": "ad_type is required"}), 400

        if not client:
            return jsonify({
                "error": "RUNWAY_API_KEY not configured"
            }), 500

        goal_prompts = {
            "awareness": "eye-catching brand awareness advertisement",
            "consideration": "engaging product showcase",
            "conversions": "conversion-focused advertisement",
            "retention": "customer retention advertisement"
        }

        base_prompt = goal_prompts.get(
            campaign_goal,
            "professional product advertisement"
        )

        prompt = (
            f"@product in {ad_type}, "
            f"{base_prompt}, "
            f"studio lighting, commercial photography, high quality"
        )

        task_info = start_runway_generation(
            image_data,
            prompt,
            filename
        )

        return jsonify({
            "success": True,
            "task_id": task_info["task_id"],
            "status": "processing",
            "message": "Image generation started"
        }), 202

    except Exception as e:
        import traceback
        print("❌ generate_assets error:", traceback.format_exc())

        return jsonify({
            "error": "Failed to start generation",
            "details": str(e),
            "type": type(e).__name__
        }), 500


@creative_assets_bp.route("/api/runway-task/<task_id>", methods=["GET"])
def get_runway_task_status(task_id):
    """
    Poll Runway task status.
    Frontend should call this every 3–5 seconds.
    """
    try:
        if not client:
            return jsonify({
                "error": "RUNWAY_API_KEY not configured"
            }), 500

        task = client.tasks.retrieve(task_id)

        if task.status == "succeeded":
            return jsonify({
                "status": "succeeded",
                "image_url": task.output[0],
                "task_id": task_id
            }), 200

        if task.status == "failed":
            return jsonify({
                "status": "failed",
                "task_id": task_id
            }), 500

        return jsonify({
            "status": task.status,
            "task_id": task_id
        }), 200

    except Exception as e:
        import traceback
        print("❌ get_runway_task_status error:", traceback.format_exc())

        return jsonify({
            "error": "Failed to fetch task status",
            "details": str(e)
        }), 500


@creative_assets_bp.route("/api/creative/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "creative-assets",
        "runway_configured": bool(client)
    }), 200
