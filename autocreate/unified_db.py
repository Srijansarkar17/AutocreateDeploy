# unified_db.py
import jwt
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

def decode_jwt_token(token):
    """Decode JWT token to get user_id"""
    try:
        if not isinstance(token, str):
            token = str(token) if token else ''
        
        token = token.strip()
        
        if not token:
            raise ValueError("Empty token")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')
        
        if not user_id:
            raise ValueError("No user_id in token payload")
        
        return str(user_id)
        
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired. Please login again.")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to decode token: {str(e)}")
    
def save_assets_to_campaign(supabase, user_id, assets_data, campaign_id):
    """Save assets to a specific campaign"""
    try:
        # Convert assets data to JSONB format
        assets_json = json.dumps(assets_data) if not isinstance(assets_data, str) else assets_data
        
        # Update the campaign with assets
        response = supabase.table('auto_create').update({
            'assets': assets_json,
            'updated_at': datetime.now().isoformat()
        }).eq('id', campaign_id).eq('user_id', user_id).execute()
        
        if response.data:
            return {
                'success': True,
                'message': 'Assets saved successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Campaign not found or access denied'
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def handle_campaign_save(supabase, current_user, data, campaign_id=None):
    """
    Unified function to handle campaign saves
    - If campaign_id provided: update that specific campaign
    - If no campaign_id: check for active campaign, if exists update it, else create new
    """
    try:
        # Convert campaign_id to integer if it's a string and not empty
        if campaign_id and isinstance(campaign_id, str):
            try:
                # Try to convert to integer (since database uses serial ID)
                campaign_id = int(campaign_id)
            except ValueError:
                # If it's not an integer, treat as None
                print(f"Warning: campaign_id is not an integer: {campaign_id}")
                campaign_id = None
        
        # Extract assets if present
        assets_data = data.pop('assets', None) or data.pop('selected_asset_ids', None)
        
        # If campaign_id is provided and is a valid integer, update that specific campaign
        if campaign_id and isinstance(campaign_id, int):
            # Check if campaign exists and belongs to user
            existing = supabase.table('auto_create').select('id').eq('id', campaign_id).eq('user_id', current_user).execute()
            
            if existing.data:
                # Update existing campaign
                data['updated_at'] = datetime.now().isoformat()
                response = supabase.table('auto_create').update(data).eq('id', campaign_id).eq('user_id', current_user).execute()
                
                if response.data and assets_data:
                    # Save assets separately
                    assets_result = save_assets_to_campaign(supabase, current_user, assets_data, campaign_id)
                    if not assets_result['success']:
                        return assets_result
                
                return {
                    'success': True,
                    'campaign_id': campaign_id,  # Return the campaign_id
                    'is_update': True
                }
            else:
                return {
                    'success': False,
                    'error': 'Campaign not found or access denied'
                }
        
        # No valid campaign_id provided - check for active campaign
        response = supabase.table('auto_create').select('id, version').eq('user_id', current_user).eq('is_active', True).execute()
        
        if response.data:
            # Active campaign exists - update it
            active_campaign = response.data[0]
            active_campaign_id = active_campaign['id']
            current_version = active_campaign.get('version', 1)
            
            # Update the active campaign
            data['updated_at'] = datetime.now().isoformat()
            data['version'] = current_version
            response = supabase.table('auto_create').update(data).eq('id', active_campaign_id).eq('user_id', current_user).execute()
            
            if response.data:
                return {
                    'success': True,
                    'campaign_id': active_campaign_id,  # Return the campaign_id
                    'is_update': True,
                    'is_new_version': False,
                    'version': current_version
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update active campaign'
                }
        
        else:
            # No active campaign - create first one
            # Let database generate the ID (serial)
            campaign_data = {
                'user_id': current_user,
                'is_active': True,
                'version': 1,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                **data
            }
            
            # Ensure required fields
            if 'budget_amount' not in campaign_data:
                campaign_data['budget_amount'] = 0.00
            if 'campaign_duration' not in campaign_data:
                campaign_data['campaign_duration'] = 1
            
            # Insert new campaign
            response = supabase.table('auto_create').insert(campaign_data).execute()
            
            if response.data:
                new_campaign_id = response.data[0]['id']
                return {
                    'success': True,
                    'campaign_id': new_campaign_id,  # Return the new campaign_id
                    'is_update': False,
                    'is_new_version': False,
                    'version': 1
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create campaign'
                }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_active_campaign(supabase, current_user, campaign_id=None):
    """Get campaign data - if campaign_id provided, get that specific one, else get active"""
    try:
        # Convert campaign_id to integer if provided
        if campaign_id and isinstance(campaign_id, str):
            try:
                campaign_id = int(campaign_id)
            except ValueError:
                # If it's not an integer, try to find by UUID or other field
                print(f"Warning: campaign_id is not an integer: {campaign_id}")
                campaign_id = None
        
        if campaign_id and isinstance(campaign_id, int):
            # Get specific campaign
            response = supabase.table('auto_create').select('*').eq('id', campaign_id).eq('user_id', current_user).execute()
        else:
            # Get active campaign
            response = supabase.table('auto_create').select('*').eq('user_id', current_user).eq('is_active', True).execute()
        
        if response.data:
            return {
                'success': True,
                'campaign': response.data[0]
            }
        else:
            return {
                'success': True,
                'campaign': None
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }