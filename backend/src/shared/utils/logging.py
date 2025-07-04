"""
ログ設定モジュール
"""
import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", format_type: str = "simple") -> logging.Logger:
    """
    アプリケーション用のログ設定を行う
    
    Args:
        level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: ログフォーマット (simple, detailed, json)
    
    Returns:
        設定済みのロガー
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # フォーマット設定
    if format_type == "detailed":
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
        )
    elif format_type == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:  # simple
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # ハンドラー設定
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得
    
    Args:
        name: ロガー名
    
    Returns:
        ロガーインスタンス
    """
    return logging.getLogger(name)


# デフォルトロガー設定
setup_logging()
logger = get_logger("proxy_server")
