# creative_assets.py
import os
import uuid
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, make_response
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
# In-memory storage (stateless-safe logic)
# --------------------------------------------------
campaigns = {}  # campaign_id -> campaign data

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

def add_cors_headers(response):
    """Helper function to add CORS headers to responses"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# --------------------------------------------------
# Routes
# --------------------------------------------------

@creative_assets_bp.route("/api/upload-image", methods=["POST", "OPTIONS"])
def upload_image():
    # Handle preflight request
    if request.method == "OPTIONS":
        response = make_response()
        return add_cors_headers(response)
    
    try:
        data = request.get_json()
        
        if not data:
            response = jsonify({"error": "No JSON data received"})
            return add_cors_headers(response), 400
        
        user_id = data.get("user_id")
        image_data = data.get("image_data")
        filename = data.get("filename", "image.png")
        ad_type = data.get("ad_type", "")
        campaign_id = data.get("campaign_id") or f"campaign_{uuid.uuid4().hex[:8]}"
        
        if not user_id or not image_data:
            response = jsonify({"error": "Missing user_id or image_data"})
            return add_cors_headers(response), 400
        
        # Remove data URI prefix if present
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        # Store campaign data
        campaigns[campaign_id] = {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "created_at": campaigns.get(campaign_id, {}).get(
                "created_at", datetime.utcnow().isoformat()
            ),
            "upload": {
                "image_data": image_data,
                "filename": filename,
                "ad_type": ad_type,
                "uploaded_at": datetime.utcnow().isoformat()
            },
            "assets": campaigns.get(campaign_id, {}).get("assets", [])
        }
        
        response = jsonify({
            "success": True,
            "campaign_id": campaign_id
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        print(f"Error in upload_image: {e}")
        traceback.print_exc()
        response = jsonify({"error": f"Server error: {str(e)}"})
        return add_cors_headers(response), 500


@creative_assets_bp.route("/api/generate-assets", methods=["POST", "OPTIONS"])
def generate_assets():
    # Handle preflight request
    if request.method == "OPTIONS":
        response = make_response()
        return add_cors_headers(response)
    
    try:
        data = request.get_json()
        
        if not data:
            response = jsonify({"error": "No JSON data received"})
            return add_cors_headers(response), 400
        
        user_id = data.get("user_id")
        campaign_id = data.get("campaign_id")
        campaign_goal = data.get("campaign_goal", "awareness")
        ad_type = data.get("ad_type")
        
        print(f"Received request: user_id={user_id}, campaign_id={campaign_id}, ad_type={ad_type}")
        
        if not user_id or not campaign_id:
            response = jsonify({"error": "Missing user_id or campaign_id"})
            return add_cors_headers(response), 400
        
        if not ad_type:
            response = jsonify({"error": "ad_type is required"})
            return add_cors_headers(response), 400
        
        # 🔥 AUTO-CREATE CAMPAIGN IF MISSING (CRITICAL FIX)
        if campaign_id not in campaigns:
            print(f"Campaign {campaign_id} not found, creating new campaign")
            campaigns[campaign_id] = {
                "campaign_id": campaign_id,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "assets": []
            }
        
        campaign = campaigns[campaign_id]
        upload = campaign.get("upload")
        
        if not upload:
            response = jsonify({
                "error": "No uploaded image found for this campaign. Please upload an image first.",
                "campaign_id": campaign_id
            })
            return add_cors_headers(response), 400
        
        # Check if Runway client is configured
        if not client:
            response = jsonify({
                "error": "Runway API is not configured. Please set RUNWAY_API_KEY environment variable."
            })
            return add_cors_headers(response), 500
        
        goal_prompts = {
            "awareness": "eye-catching brand awareness advertisement",
            "consideration": "engaging product showcase",
            "conversions": "conversion-focused advertisement",
            "retention": "customer retention advertisement"
        }
        
        base_prompt = goal_prompts.get(
            campaign_goal, "professional product advertisement"
        )
        
        prompts = [
            f"@product in {ad_type}, {base_prompt}, studio lighting, commercial photography",
            f"@product in {ad_type}, lifestyle setting, natural lighting, modern aesthetic",
            f"@product in {ad_type}, minimalist design, bold colors, marketing focused",
            f"@product in {ad_type}, creative concept, premium quality",
            f"@product in {ad_type}, social media optimized, vibrant colors"
        ]
        
        assets = []
        errors = []
        
        for i, prompt in enumerate(prompts):
            try:
                print(f"Generating image {i+1}/5 with prompt: {prompt}")
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
                    "type": "ai_generated",
                    "task_id": result.get("task_id")
                })
                print(f"✓ Successfully generated image {i+1}/5")
                
            except Exception as e:
                error_msg = f"Failed to generate variation {i+1}: {str(e)}"
                print(error_msg)
                traceback.print_exc()
                errors.append(error_msg)
        
        if not assets:
            response = jsonify({
                "error": "Failed to generate any assets",
                "details": errors
            })
            return add_cors_headers(response), 500
        
        # Save generated assets
        campaign["assets"] = assets
        campaign["updated_at"] = datetime.utcnow().isoformat()
        
        print(f"✓ Successfully generated {len(assets)} assets for campaign {campaign_id}")
        
        response = jsonify({
            "success": True,
            "campaign_id": campaign_id,
            "assets": assets,
            "warnings": errors if errors else None
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        print(f"Error in generate_assets: {e}")
        traceback.print_exc()
        response = jsonify({"error": f"Server error: {str(e)}"})
        return add_cors_headers(response), 500


@creative_assets_bp.route("/api/save-selected-assets", methods=["POST", "OPTIONS"])
def save_selected_assets():
    # Handle preflight request
    if request.method == "OPTIONS":
        response = make_response()
        return add_cors_headers(response)
    
    try:
        data = request.get_json()
        campaign_id = data.get("campaign_id")
        selected_assets = data.get("selected_assets", [])
        
        if campaign_id not in campaigns:
            response = jsonify({"error": "Campaign not found"})
            return add_cors_headers(response), 404
        
        campaigns[campaign_id]["selected_assets"] = selected_assets
        campaigns[campaign_id]["updated_at"] = datetime.utcnow().isoformat()
        
        response = jsonify({
            "success": True,
            "saved": len(selected_assets)
        })
        return add_cors_headers(response), 200
        
    except Exception as e:
        print(f"Error in save_selected_assets: {e}")
        traceback.print_exc()
        response = jsonify({"error": f"Server error: {str(e)}"})
        return add_cors_headers(response), 500


@creative_assets_bp.route("/api/creative/health", methods=["GET", "OPTIONS"])
def health():
    # Handle preflight request
    if request.method == "OPTIONS":
        response = make_response()
        return add_cors_headers(response)
    
    response = jsonify({
        "status": "healthy",
        "service": "creative-assets",
        "runway_configured": bool(client),
        "campaign_count": len(campaigns)
    })
    return add_cors_headers(response), 200