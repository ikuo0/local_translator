"""Main Flask application for impl_translator UI.

Routing structure:
- / -> impl_translator/src/app/html/ (static files and index)
- /sr1001 -> impl_translator/src/features/SR1001/html/ (static files)
- /sr1001/api/* -> SR1001 Blueprint API routes
"""

from flask import Flask, send_from_directory
from pathlib import Path


def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    
    # Get base paths
    app_html_path = Path(__file__).parent / "html"
    sr1001_html_path = Path(__file__).parent.parent / "features" / "SR1001" / "html"
    
    # API routes from SR features (register FIRST to have priority)
    from impl_translator.src.features.SR1001.app import bp as sr1001_bp
    app.register_blueprint(sr1001_bp)
    
    # SR1001 index route
    @app.route("/sr1001/")
    def sr1001_index():
        """Serve SR1001 index.html from SR1001/html/."""
        return send_from_directory(sr1001_html_path, "index.html")
    
    # SR1001 static files (must come AFTER sr1001_index to avoid conflict)
    @app.route("/sr1001/<path:filename>")
    def serve_sr1001_static(filename: str):
        """Serve static files from SR1001/html/ directory."""
        try:
            return send_from_directory(sr1001_html_path, filename)
        except Exception:
            return {"error": f"File not found: {filename}"}, 404
    
    # Root index route
    @app.route("/")
    def root_index():
        """Serve root index.html from app/html/."""
        return send_from_directory(app_html_path, "index.html")
    
    # Root static files - serve from app/html/ (must be LAST to avoid conflicts)
    @app.route("/<path:filename>")
    def serve_root_static(filename: str):
        """Serve static files from app/html/ directory."""
        try:
            return send_from_directory(app_html_path, filename)
        except Exception:
            return {"error": f"File not found: {filename}"}, 404
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
