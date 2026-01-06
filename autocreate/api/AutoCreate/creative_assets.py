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


def generate_image_with_runway(image_b64: str, prompt: str, filename: str):
    if not client:
        raise RuntimeError("RUNWAY_API_KEY not configured")

    mime = get_mime_type(filename)
    data_uri = f"data:{mime};base64,{image_b64}"

    task = client.text_to_image.create(
        model="gen4_image_turbo",
        ratio="1080:1080",
        prompt_text=prompt,
        reference_images=[{
            "uri": data_uri,
            "tag": "product"
        }],
    )

    result = task.wait_for_task_output()

    if not result or not result.output:
        raise RuntimeError("Runway returned no output")

    return {
        "image_url": result.output[0],
        "task_id": task.id
    }


# --------------------------------------------------
# ROUTES (STATELESS, PRODUCTION SAFE)
# --------------------------------------------------
@creative_assets_bp.route("/api/generate-assets", methods=["POST"])
def generate_assets():
    try:
        data = request.get_json(force=True)
        
        print(f"📥 Received request with keys: {data.keys() if data else 'No data'}")
        
        image_data = data.get("image_data")
        filename = data.get("filename", "image.png")
        campaign_goal = data.get("campaign_goal", "awareness")
        ad_type = data.get("ad_type")

        if not image_data:
            print("❌ No image_data provided")
            return jsonify({"error": "image_data is required"}), 400

        if not ad_type:
            print("❌ No ad_type provided")
            return jsonify({"error": "ad_type is required"}), 400

        print(f"✅ Valid input received: ad_type={ad_type}, filename={filename}, image_data_length={len(image_data) if image_data else 0}")

        # Check if Runway client is configured
        if not client:
            print("❌ Runway client not configured - RUNWAY_API_KEY missing")
            raise RuntimeError("RUNWAY_API_KEY not configured in environment variables")

        print("✅ Runway client is configured")

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

        prompts = [
            f"@product in {ad_type}, {base_prompt}, studio lighting, commercial photography",
            f"@product in {ad_type}, lifestyle setting, natural lighting, modern aesthetic",
            f"@product in {ad_type}, minimalist design, bold colors, marketing focused",
            f"@product in {ad_type}, creative concept, premium quality",
            f"@product in {ad_type}, social media optimized, vibrant colors"
        ]

        assets = []
        
        # Test with just ONE image first to debug
        print(f"🚀 Starting generation with prompt: {prompts[0]}")
        
        try:
            result = generate_image_with_runway(
                image_data,
                prompts[0],
                filename
            )
            
            print(f"✅ First image generated successfully: {result['image_url'][:50]}...")
            
            assets.append({
                "id": 1,
                "title": f"{ad_type} – Variation 1",
                "image_url": result["image_url"],
                "prompt": prompts[0],
                "score": 85,
                "task_id": result["task_id"],
                "type": "ai_generated"
            })
            
            return jsonify({
                "success": True,
                "assets": assets,
                "test_mode": True,
                "message": "Generated 1 image for testing"
            }), 200
            
        except Exception as gen_error:
            print(f"❌ Error in generate_image_with_runway: {str(gen_error)}")
            raise gen_error

    except Exception as e:
        print("❌ Generation error:", str(e))
        import traceback
        print("Traceback:", traceback.format_exc())
        
        return jsonify({
            "error": "Failed to generate assets",
            "details": str(e),
            "type": type(e).__name__
        }), 500


@creative_assets_bp.route("/api/creative/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "creative-assets",
        "runway_configured": bool(client)
    }), 200
