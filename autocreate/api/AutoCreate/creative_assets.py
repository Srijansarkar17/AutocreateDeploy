from flask import Blueprint, request, jsonify
import os
import traceback
from datetime import datetime
import uuid
from runwayml import RunwayML, TaskFailedError

# Create Blueprint - renamed to match main.py import
creative_assets_bp = Blueprint('creative_assets', __name__, url_prefix='/api/creatives')

# Initialize Runway ML client
RUNWAY_API_KEY = os.environ.get('RUNWAY_API_KEY', '')
client = RunwayML(api_key=RUNWAY_API_KEY) if RUNWAY_API_KEY else None

# Storage for campaigns and assets (in production, use a database)
campaigns = {}
user_uploads = {}

def get_mime_type_from_filename(filename):
    """Get MIME type from filename"""
    file_extension = filename.lower().split('.')[-1]
    mime_type_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'webp': 'image/webp'
    }
    return mime_type_map.get(file_extension, 'image/png')

def generate_image_with_runway(image_data_base64, prompt_text, filename='image.png'):
    """Generate image using Runway ML Text-to-Image API with reference image"""
    try:
        if not client:
            raise Exception("Runway client not initialized. Please set RUNWAY_API_KEY")
        
        mime_type = get_mime_type_from_filename(filename)
        data_uri = f"data:{mime_type};base64,{image_data_base64}"
        
        print(f"Creating generation task with prompt: {prompt_text[:100]}...")
        
        task = client.text_to_image.create(
            model='gen4_image_turbo',
            ratio='1080:1080',
            prompt_text=prompt_text,
            reference_images=[
                {
                    'uri': data_uri,
                    'tag': 'product',
                }
            ]
        )
        
        print(f"Task created with ID: {task.id}, waiting for completion...")
        result = task.wait_for_task_output()
        print(f"✓ Task completed successfully!")
        
        if result and hasattr(result, 'output') and result.output:
            image_url = result.output[0] if isinstance(result.output, list) else result.output
            return {
                'success': True,
                'image_url': image_url,
                'task_id': task.id
            }
        else:
            print(f"✗ No output in result: {result}")
            return None
            
    except TaskFailedError as e:
        print(f"✗ Task failed: {e.task_details}")
        return None
    except Exception as e:
        print(f"✗ Error generating image: {str(e)}")
        traceback.print_exc()
        return None

@creative_assets_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """Handle image upload and store for later generation"""
    try:
        data = request.json
        user_id = data.get('user_id')
        image_data = data.get('image_data')
        filename = data.get('filename', 'uploaded_image.png')
        campaign_id = data.get('campaign_id')
        ad_type = data.get('ad_type', '')
        
        if not user_id or not image_data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if not campaign_id:
            campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
        
        if user_id not in user_uploads:
            user_uploads[user_id] = {}
        
        user_uploads[user_id][campaign_id] = {
            'image_data': image_data,
            'filename': filename,
            'ad_type': ad_type,
            'uploaded_at': datetime.now().isoformat()
        }
        
        if campaign_id not in campaigns:
            campaigns[campaign_id] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'assets': []
            }
        
        print(f"✓ Image uploaded for campaign {campaign_id}")
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'message': 'Image uploaded successfully'
        })
        
    except Exception as e:
        print(f"✗ Error in upload_image: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@creative_assets_bp.route('/generate-assets', methods=['POST'])
def generate_assets():
    """Generate images using Runway ML when both image and text are provided"""
    try:
        data = request.json
        user_id = data.get('user_id')
        campaign_id = data.get('campaign_id')
        campaign_goal = data.get('campaign_goal', 'awareness')
        ad_type = data.get('ad_type', '')
        
        if not user_id or not campaign_id:
            return jsonify({'success': False, 'error': 'Missing user_id or campaign_id'}), 400
        
        if user_id not in user_uploads or campaign_id not in user_uploads[user_id]:
            return jsonify({'success': False, 'error': 'No uploaded image found'}), 400
        
        upload_info = user_uploads[user_id][campaign_id]
        image_data = upload_info['image_data']
        filename = upload_info['filename']
        
        if ad_type:
            upload_info['ad_type'] = ad_type
        else:
            ad_type = upload_info.get('ad_type', '')
        
        if not ad_type:
            return jsonify({
                'success': False,
                'error': 'Please provide the type of ads you want to generate'
            }), 400
        
        print("=" * 60)
        print(f"🎨 Starting image generation for campaign: {campaign_id}")
        print(f"📝 Ad Type: {ad_type}")
        print(f"🎯 Goal: {campaign_goal}")
        print("=" * 60)
        
        goal_prompts = {
            'awareness': 'eye-catching brand awareness advertisement',
            'consideration': 'engaging product showcase for consideration',
            'conversions': 'compelling conversion-focused advertisement',
            'retention': 'loyalty-building customer retention ad',
            'lead': 'professional lead generation advertisement'
        }
        
        base_prompt = goal_prompts.get(campaign_goal, 'professional product advertisement')
        
        prompts = [
            f"@product in {ad_type}, {base_prompt}, professional commercial photography, high quality, studio lighting, product focus",
            f"@product in {ad_type}, {base_prompt}, lifestyle setting, natural lighting, modern aesthetic, clean composition",
            f"@product in {ad_type}, {base_prompt}, minimalist design, bold colors, contemporary style, marketing focused",
            f"@product in {ad_type}, {base_prompt}, creative concept, attention-grabbing, premium quality, advertisement optimized",
            f"@product in {ad_type}, {base_prompt}, social media optimized, vibrant colors, engaging composition, trendy design"
        ]
        
        generated_assets = []
        
        print(f"🚀 Generating {len(prompts)} image variations...")
        
        for idx, prompt in enumerate(prompts):
            print(f"\n[{idx + 1}/{len(prompts)}] Generating variation...")
            print(f" Prompt: {prompt[:80]}...")
            
            result = generate_image_with_runway(image_data, prompt, filename)
            
            if result and result.get('success'):
                generated_assets.append({
                    'id': idx + 1,
                    'title': f'{ad_type} - Variation {idx + 1}',
                    'image_url': result['image_url'],
                    'prompt': prompt,
                    'score': 85 + (idx * 2),
                    'type': 'AI Generated',
                    'task_id': result['task_id']
                })
                print(f" ✓ Success! Image URL: {result['image_url'][:50]}...")
            else:
                print(f" ✗ Failed to generate variation {idx + 1}")
        
        if len(generated_assets) == 0:
            return jsonify({
                'success': False,
                'error': 'Failed to generate any images. Please check your Runway API key and credits.'
            }), 500
        
        if campaign_id in campaigns:
            campaigns[campaign_id]['assets'] = generated_assets
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully generated {len(generated_assets)} images!")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'assets': generated_assets,
            'campaign_id': campaign_id,
            'message': f'Successfully generated {len(generated_assets)} images'
        })
        
    except Exception as e:
        print(f"\n✗ Error in generate_assets: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@creative_assets_bp.route('/save-selected-assets', methods=['POST'])
def save_selected_assets():
    """Save selected assets to the campaign"""
    try:
        data = request.json
        user_id = data.get('user_id')
        campaign_id = data.get('campaign_id')
        selected_assets = data.get('selected_assets', [])
        
        if not user_id or not campaign_id:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        if campaign_id not in campaigns:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        campaigns[campaign_id]['selected_assets'] = selected_assets
        campaigns[campaign_id]['updated_at'] = datetime.now().isoformat()
        
        print(f"✓ Saved {len(selected_assets)} selected assets for campaign {campaign_id}")
        
        return jsonify({
            'success': True,
            'message': f'{len(selected_assets)} assets saved successfully'
        })
        
    except Exception as e:
        print(f"✗ Error in save_selected_assets: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@creative_assets_bp.route('/create-campaign', methods=['POST'])
def create_campaign():
    """Create a new campaign"""
    try:
        data = request.json
        user_id = data.get('user_id')
        campaign_goal = data.get('campaign_goal', 'awareness')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
        campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
        
        campaigns[campaign_id] = {
            'user_id': user_id,
            'campaign_goal': campaign_goal,
            'created_at': datetime.now().isoformat(),
            'assets': []
        }
        
        print(f"✓ Created new campaign: {campaign_id}")
        
        return jsonify({
            'success': True,
            'campaign_id': campaign_id
        })
        
    except Exception as e:
        print(f"✗ Error in create_campaign: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@creative_assets_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'runway-image-generation',
        'api_key_set': client is not None
    })