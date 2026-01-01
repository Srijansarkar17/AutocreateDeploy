"""
AutoCreate Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Server ports
    MAIN_PORT_2 = int(os.getenv("MAIN_PORT_2", 5014))
    AUDIENCE_PORT = int(os.getenv("AUDIENCE_PORT", 5006))
    BUDGET_TESTING_PORT = int(os.getenv("BUDGET_TESTING_PORT", 5012))
    CAMPAIGN_GOAL_PORT = int(os.getenv("CAMPAIGN_GOAL_PORT", 5005))
    COPY_MESSAGING_PORT = int(os.getenv("COPY_MESSAGING_PORT", 5013))
    CREATIVE_ASSETS_PORT = int(os.getenv("CREATIVE_ASSETS_PORT", 5017))  # Added Creative Assets port
    
    # JWT Configuration (should be same as AdSurveillance for shared auth)
    SECRET_KEY = os.getenv("SECRET_KEY", "your-fallback-secret-key-change-in-production")
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    
    # Groq API (for copy messaging)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    
    # Runway ML API (for creative assets)
    RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
    
    # CORS Configuration
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://192.0.0.2:5173",
    ]

settings = Settings()