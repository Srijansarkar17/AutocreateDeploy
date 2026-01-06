import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# ✅ PROPER CORS CONFIGURATION
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     supports_credentials=False)  # Set to False when using origins="*"

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

# ✅ ADD EXPLICIT OPTIONS HANDLER FOR ALL ROUTES
@app.before_request
def handle_preflight():
    from flask import request
    if request.method == "OPTIONS":
        from flask import make_response
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        return response

# ✅ ADD CORS HEADERS TO ALL RESPONSES
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
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