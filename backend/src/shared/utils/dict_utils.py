"""
ユーティリティ関数
"""
from typing import Any, Dict
import json


def to_dict(obj: Any) -> Dict:
    """オブジェクトを辞書に変換"""
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return obj


def to_json(obj: Any) -> str:
    """オブジェクトをJSONに変換"""
    return json.dumps(to_dict(obj), default=str)
