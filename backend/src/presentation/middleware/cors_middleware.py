"""
CORS ミドルウェア
"""
from fastapi import FastAPI


def setup_cors_middleware(app: FastAPI, frontend_origins: list[str]):
    """CORS ミドルウェア設定"""
    from fastapi.middleware.cors import CORSMiddleware
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,  # ["http://localhost:3000"]
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
