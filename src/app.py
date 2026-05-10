from flask import Flask
from flask_cors import CORS
# from routes.auth_routes import auth_bp
from src.routes.auth_routes import auth_bp

import os

app = Flask(__name__)

CORS(
    app,
    origins=[f"{os.getenv('FRONTEND_URL')}"],
    supports_credentials=True  
)

app.register_blueprint(auth_bp, url_prefix="/auth")

if __name__ == "__main__":
    app.run(debug=True)