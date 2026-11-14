from flask import jsonify


def json_response(code: int, message: str, data=None):
    return jsonify(
        {
            "code": code,
            "message": message,
            "data": data,
        }
    ), code
