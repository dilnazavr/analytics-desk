from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config_by_name
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.cases import cases_bp
    from app.api.files import files_bp
    from app.api.invoices import invoices_bp
    from app.api.matches import matches_bp
    from app.api.reports import reports_bp
    from app.api.dashboard import dashboard_bp
    from app.api.graph import graph_bp
    from app.api.users import users_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(cases_bp, url_prefix="/api/cases")
    app.register_blueprint(files_bp, url_prefix="/api/files")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(matches_bp, url_prefix="/api/matches")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(graph_bp, url_prefix="/api")
    app.register_blueprint(users_bp, url_prefix="/api/users")

    @app.route("/api/health")
    def health():
        return {"status": "ok", "service": "Analytics Desk API"}

    return app
