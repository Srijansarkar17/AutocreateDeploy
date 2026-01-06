import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

# --------------------------------------------------
# CORS (IMPORTANT)
# --------------------------------------------------
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=False
)


# --------------------------------------------------
# Handle OPTIONS Preflight (Gunicorn-safe)
# --------------------------------------------------
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_response("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

# --------------------------------------------------
# Blueprints
# --------------------------------------------------
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

# --------------------------------------------------
# Health Routes
# --------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    return {"service": "AutoCreate", "status": "running"}

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

# --------------------------------------------------
# Entrypoint (local only)
# --------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
