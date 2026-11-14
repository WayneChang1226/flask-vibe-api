import os
import re
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, Response, request
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import HTTPException

from extensions import db
from routes import (
    accounts_bp,
    transfers_bp,
    income_categories_bp,
    incomes_bp,
    expense_categories_bp,
    expenses_bp,
    invoices_bp,
    draw_periods_bp,
    instruments_bp,
    trades_bp,
    summary_bp,
)
from utils import json_response


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False

    # 若程序環境變數中尚未設定 DATABASE_URL，嘗試載入專案目錄的 .env
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("缺少環境變數 DATABASE_URL，無法啟動應用程式。請在環境變數或 .env 檔案中指定有效的 PostgreSQL 連線字串。")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    def is_allowed_origin(origin: str | None) -> bool:
        if not origin:
            return False
        web_origin = os.getenv("WEB_ORIGIN")
        if web_origin and origin == web_origin.strip():
            return True
        if re.match(r"^http://127\.0\.0\.1(:\d+)?$", origin):
            return True
        if re.match(r"^http://localhost(:\d+)?$", origin):
            return True
        return False

    @app.before_request
    def handle_cors_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get("Origin")
            if is_allowed_origin(origin):
                response = Response(status=204)
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
                req_headers = request.headers.get("Access-Control-Request-Headers")
                if req_headers:
                    response.headers["Access-Control-Allow-Headers"] = req_headers
                else:
                    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                response.headers["Access-Control-Allow-Private-Network"] = "true"
                response.headers["Access-Control-Max-Age"] = "86400"
                response.headers["Vary"] = "Origin"
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
                return response

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, PUT, DELETE, OPTIONS"
            req_headers = request.headers.get("Access-Control-Request-Headers")
            if req_headers:
                response.headers["Access-Control-Allow-Headers"] = req_headers
            response.headers["Access-Control-Allow-Private-Network"] = "true"

        vary = response.headers.get("Vary")
        if not vary:
            response.headers["Vary"] = "Origin"
        elif "Origin" not in [v.strip() for v in vary.split(",")]:
            response.headers["Vary"] = f"{vary}, Origin"

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return response

    app.register_blueprint(accounts_bp)
    app.register_blueprint(transfers_bp)
    app.register_blueprint(income_categories_bp)
    app.register_blueprint(incomes_bp)
    app.register_blueprint(expense_categories_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(draw_periods_bp)
    app.register_blueprint(instruments_bp)
    app.register_blueprint(trades_bp)
    app.register_blueprint(summary_bp)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        if error.code == 404:
            return json_response(404, "找不到指定的資源", None)
        return json_response(error.code, error.description, None)

    @app.errorhandler(OperationalError)
    def handle_operational_error(error):
        app.logger.error("資料庫連線錯誤: %s", error, exc_info=True)
        return json_response(500, "資料庫暫時連不上", None)

    @app.get("/api/health")
    def health_check():
        return json_response(
            200,
            "伺服器運作正常，測試正常可以進行其他任務。",
            {
                "status": "ok",
                "time": datetime.now(timezone.utc).isoformat(),
            },
        )

    @app.get("/api/health/db")
    def health_db_check():
        try:
            db.session.execute(text("SELECT 1"))
            return json_response(
                200,
                "資料庫連線正常",
                {"status": "ok"},
            )
        except Exception as e:
            app.logger.error("資料庫連線檢查失敗: %s", e, exc_info=True)
            return json_response(
                500,
                "資料庫暫時連不上",
                None,
            )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)