import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from werkzeug.exceptions import HTTPException

from extensions import db
from routes import accounts_bp, transfers_bp, income_categories_bp, incomes_bp
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

    app.register_blueprint(accounts_bp)
    app.register_blueprint(transfers_bp)
    app.register_blueprint(income_categories_bp)
    app.register_blueprint(incomes_bp)

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