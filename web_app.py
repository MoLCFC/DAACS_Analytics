"""Flask web application providing DAACS analytics APIs and dashboards."""

from __future__ import annotations

import argparse
import logging
import traceback
from datetime import datetime
from typing import Dict, Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from database import MongoRepository
from analytics import AnalyticsEngine


def create_app(repo: MongoRepository) -> Flask:
    app = Flask(__name__, static_folder="static")
    CORS(app)
    engine = AnalyticsEngine(repo)

    @app.route("/api/health")
    def health() -> Any:
        try:
            repo.users.find_one({}, {"_id": 1})
            return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})
        except Exception as exc:
            return jsonify({"status": "unhealthy", "error": str(exc)}), 503

    @app.route("/api/system/dashboard")
    def system_dashboard() -> Any:
        try:
            data = engine.system_dashboard()
            return jsonify(data)
        except Exception as exc:
            logging.exception("system dashboard failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/<user_id>/analytics")
    def user_analytics(user_id: str) -> Any:
        try:
            data = engine.user_analytics(user_id)
            if "error" in data:
                return jsonify(data), 404
            return jsonify(data)
        except Exception as exc:
            logging.exception("user analytics failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/<user_id>/events")
    def user_events(user_id: str) -> Any:
        try:
            return jsonify(engine.event_summary(user_id))
        except Exception as exc:
            logging.exception("event summary failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/assessments/activity")
    def assessments_activity() -> Any:
        try:
            start = request.args.get("start")
            end = request.args.get("end")
            return jsonify(engine.assessments_activity(start, end))
        except Exception as exc:
            logging.exception("assessments activity failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/assessments/answers")
    def answer_counts() -> Any:
        try:
            year = request.args.get("year")
            if year:
                return jsonify(engine.answer_counts_year(int(year)))
            start = request.args.get("start")
            end = request.args.get("end")
            return jsonify(engine.answer_counts(start, end))
        except Exception as exc:
            logging.exception("answer counts failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/assessments/ridgeline")
    def assessments_ridgeline() -> Any:
        try:
            assessment_id = request.args.get("assessmentId")
            category = request.args.get("category")
            return jsonify(engine.ridgeline_answer_options(assessment_id, category))
        except Exception as exc:
            logging.exception("ridgeline failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/assessments/list")
    def assessments_list() -> Any:
        try:
            q = request.args.get("q")
            limit = int(request.args.get("limit", 25))
            category = request.args.get("category")
            return jsonify(engine.list_assessments(q, limit, category))
        except Exception as exc:
            logging.exception("assessments list failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/assessments/timing")
    def assessment_timing() -> Any:
        try:
            return jsonify(engine.assessment_timings())
        except Exception as exc:
            logging.exception("assessment timing failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/<user_id>/navigation")
    def user_navigation(user_id: str) -> Any:
        try:
            start = request.args.get("start")
            end = request.args.get("end")
            return jsonify(engine.navigation_flow(user_id, start, end))
        except Exception as exc:
            logging.exception("navigation flow failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/created")
    def users_created() -> Any:
        try:
            start = request.args.get("start")
            end = request.args.get("end")
            return jsonify(engine.users_created(start, end))
        except Exception as exc:
            logging.exception("users created failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/with_navigation")
    def users_with_navigation() -> Any:
        try:
            start = request.args.get("start")
            end = request.args.get("end")
            return jsonify(engine.users_with_navigation(start, end))
        except Exception as exc:
            logging.exception("users with navigation failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/logins/heatmap")
    def users_logins_heatmap() -> Any:
        try:
            year = request.args.get("year")
            if year:
                return jsonify(engine.logins_heatmap_year(int(year)))
            start = request.args.get("start")
            end = request.args.get("end")
            return jsonify(engine.logins_heatmap(start, end))
        except Exception as exc:
            logging.exception("logins heatmap failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/logins/daily")
    def users_logins_daily() -> Any:
        try:
            year = int(request.args.get("year", datetime.now().year))
            month = request.args.get("month")
            if month:
                return jsonify(engine.logins_daily_month(year, int(month)))
            return jsonify(engine.logins_daily_year(year))
        except Exception as exc:
            logging.exception("logins daily failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users/top")
    def top_students() -> Any:
        try:
            limit = int(request.args.get("limit", 100))
            return jsonify(engine.top_students(limit))
        except Exception as exc:
            logging.exception("top students failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/api/users")
    def list_users() -> Any:
        try:
            limit = int(request.args.get("limit", 20))
            query = request.args.get("q")
            users = repo.fetch_users(limit=limit, query=query)
            return jsonify([
                {
                    "id": user.id,
                    "name": user.full_name,
                    "username": user.username,
                    "roles": user.roles,
                }
                for user in users
            ])
        except Exception as exc:
            logging.exception("list users failed")
            return jsonify({"error": str(exc), "traceback": traceback.format_exc()}), 500

    @app.route("/")
    def index() -> Any:
        return send_from_directory(app.static_folder, "dashboard.html")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="DAACS analytics server")
    parser.add_argument("--connection-string", default="mongodb://localhost:27017/")
    parser.add_argument("--database", default="daacs_analytics")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    repo = MongoRepository(args.connection_string, args.database)
    app = create_app(repo)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
