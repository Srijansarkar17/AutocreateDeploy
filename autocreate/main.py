import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# Configure CORS with more specific settings
CORS(app, 
     origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],  # Add your frontend origins
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)

# OR for development only, you can use:
# CORS(app, resources={r"/api/*": {"origins": "*"}})

from autocreate.api.AutoCreate.audience_step import audience_bp
from autocreate.api.AutoCreate.budget_testing import budget_testing_bp
from autocreate.api.AutoCreate.campaign_goal import campaign_goal_bp
from autocreate.api.AutoCreate.copy_messaging import copy_messaging_bp
from autocreate.api.AutoCreate.creative_assets import creative_assets_bp

app.register_blueprint(audience_bp)
app.register_blueprint(budget_testing_bp)
app.register_blueprint(campaign_goal_bp)
app.register_blueprint(copy_messaging_bp)
app.register_blueprint(creative_assets_bp)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:5173')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route("/")
def root():
    return {"service": "AutoCreate", "status": "running"}

@app.route("/health")
def health():
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)