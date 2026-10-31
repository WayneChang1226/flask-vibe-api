from datetime import datetime, timezone

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.json.ensure_ascii = False

tasks = [
    {
        "id": 1,
        "title": "範例任務",
        "description": "這是一筆記憶體中的模擬任務。",
    }
]
next_task_id = 2


def json_response(status, message, data, http_status):
    return jsonify(
        {
            "status": status,
            "message": message,
            "data": data,
        }
    ), http_status


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    return json_response("error", error.description, None, error.code)


@app.get("/api/health")
def health_check():
    return json_response(
        "success",
        "伺服器運作正常",
        {
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        200,
    )


@app.get("/api/tasks")
def get_tasks():
    return json_response("success", "取得任務清單成功", tasks, 200)


@app.post("/api/tasks")
def create_task():
    global next_task_id

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return json_response("error", "請提供合法的 JSON 物件", None, 400)

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return json_response("error", "必填欄位 title 不可為空", None, 400)

    task = {
        "id": next_task_id,
        "title": title.strip(),
        "description": payload.get("description", ""),
    }
    tasks.append(task)
    next_task_id += 1

    return json_response("success", "新增任務成功", task, 201)


@app.get("/api/tasks/<int:task_id>")
def get_task(task_id):
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task is None:
        return json_response("error", "找不到指定任務", None, 404)

    return json_response("success", "取得任務成功", task, 200)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)