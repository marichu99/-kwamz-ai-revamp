# utils/response_utils.py
from flask import jsonify
from typing import Any, Dict, Optional

def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    **additional_fields
) -> tuple:
    """Create a standardized success response"""
    response = {
        "success": True,
        "message": message,
        "data": data
    }
    response.update(additional_fields)
    return jsonify(response), status_code

def error_response(
    message: str = "An error occurred",
    status_code: int = 500,
    error_code: Optional[str] = None,
    details: Any = None
) -> tuple:
    """Create a standardized error response"""
    response = {
        "success": False,
        "message": message,
        "error": {
            "code": error_code,
            "message": message,
            "details": details
        }
    }
    return jsonify(response), status_code