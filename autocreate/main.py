import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://markos-awjq.vercel.app", "http://localhost:5173"], allow_headers=["Content-Type", "Authorization"],supports_credentials=True)

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

@app.route("/")
def root():
    return {"service": "AutoCreate", "status": "running"}

@app.route("/health")
def health():
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
