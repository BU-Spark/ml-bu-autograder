#!/usr/bin/env python3
"""
app.py — Flask application factory for the AI Auto Grader.

Run:
    python scripts/web/app.py

Then open:  http://localhost:5000
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so all internal imports resolve correctly.
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from flask import Flask, jsonify, render_template

from web.config import (
    DEFAULT_LECTURE_CHUNKS,
    DEFAULT_RUBRIC_DIR,
    LIBRARY_ASSIGNMENTS_DIR,
    LIBRARY_QUIZZES_DIR,
    LIBRARY_RUBRICS_DIR,
    PROJECT_ROOT,
    PROVIDERS,
    RUBRIC_ALLOWED_EXTS,
)
from web.utils.files import _discover_files
from web.utils.pipeline import _shared_chroma_ready

from web.blueprints.grading  import grading_bp
from web.blueprints.lecture  import lecture_bp
from web.blueprints.library  import library_bp
from web.blueprints.rubric   import rubric_bp
from web.blueprints.reports  import reports_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

    app.register_blueprint(grading_bp)
    app.register_blueprint(lecture_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(rubric_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        rubrics = (
            _discover_files(DEFAULT_RUBRIC_DIR, kind="rubric") +
            _discover_files(LIBRARY_RUBRICS_DIR, exts=RUBRIC_ALLOWED_EXTS, kind="rubric")
        )
        assignments = (
            _discover_files(PROJECT_ROOT / "assignments") +
            _discover_files(LIBRARY_ASSIGNMENTS_DIR)
        )
        quizzes = _discover_files(LIBRARY_QUIZZES_DIR)
        return render_template(
            "index.html",
            providers=PROVIDERS,
            rubrics=rubrics,
            assignments=assignments,
            quizzes=quizzes,
            lecture_chunks_exist=DEFAULT_LECTURE_CHUNKS.exists(),
            shared_chroma_ready=_shared_chroma_ready(),
        )

    @app.route("/api/providers")
    def api_providers():
        return jsonify(PROVIDERS)

    @app.errorhandler(413)
    def payload_too_large(_err):
        return jsonify(success=False, error="Uploaded file is too large (max 200 MB)."), 413

    return app


app = create_app()

if __name__ == "__main__":
    print("\n  AI Auto Grader — Web Interface")
    print("  http://localhost:5000\n")
    debug = str(os.getenv("FLASK_DEBUG", "0")).strip().lower() in {"1", "true", "yes"}
    host  = os.getenv("FLASK_HOST", "127.0.0.1")
    port  = int(os.getenv("FLASK_PORT", "5000"))
    app.run(debug=debug, host=host, port=port)
