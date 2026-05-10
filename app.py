from flask import Flask
from flask_cors import CORS
# from routes.auth_routes import auth_bp
from src.routes.auth_routes import auth_bp


import os

app = Flask(__name__)

print('frontend url',os.getenv('FRONTEND_URL'))

CORS(
    app,
    origins=['https://ai-attendance-frontend.vercel.app'],
    supports_credentials=True  
)

@app.route("/")
def home():
    return {
        "success": True,
        "message": "AI Attendance Backend Running 🚀"
    }

        

app.register_blueprint(auth_bp, url_prefix="/auth")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )