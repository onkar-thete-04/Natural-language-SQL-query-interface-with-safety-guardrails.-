from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import ExecuteRequest, FeedbackRequest, QueryRequest
from shared.config import Settings
from shared.errors import (
    ExecutionError,
    GuardrailError,
    LLMClientError,
    SchemaIntrospectionError,
    SQLValidationError,
)
from shared.serialization import to_dict


def create_app(service=None, store=None) -> FastAPI:
    settings = Settings()
    if service is None:
        from pipeline.service import PipelineService
        service = PipelineService(settings)
    if store is None:
        from store.repository import Store
        store = Store(settings.sqlite_db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = service
        app.state.store = store
        app.state.settings = settings
        yield

    app = FastAPI(title="Text-to-SQL API", version="0.1.0", lifespan=lifespan)

    app.state.service = service
    app.state.store = store
    app.state.settings = settings

    @app.exception_handler(SQLValidationError)
    @app.exception_handler(GuardrailError)
    async def _bad_request(request, exc):
        return JSONResponse(status_code=400, content=_error(exc))

    @app.exception_handler(LLMClientError)
    async def _bad_gateway(request, exc):
        return JSONResponse(status_code=502, content=_error(exc))

    @app.exception_handler(ExecutionError)
    @app.exception_handler(SchemaIntrospectionError)
    async def _internal_error(request, exc):
        return JSONResponse(status_code=500, content=_error(exc))

    @app.post("/v1/query")
    def post_query(body: QueryRequest):
        result = app.state.service.run(body.question)
        query_id = str(uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        result_dict = to_dict(result)
        app.state.store.save_query(
            query_id=query_id,
            session_id=body.session_id,
            question=body.question,
            sql=result.generated_sql.sql,
            confidence=result.confidence_report.overall,
            result_json=result_dict,
            created_at=created_at,
        )
        return {"query_id": query_id, "session_id": body.session_id, **result_dict}

    @app.post("/v1/execute")
    def post_execute(body: ExecuteRequest):
        return app.state.service.run_sql(body.sql)

    @app.get("/v1/schema")
    def get_schema():
        return to_dict(app.state.service.get_schema())

    @app.get("/v1/history")
    def get_history(session_id: str = "default"):
        return app.state.store.get_history(session_id)

    @app.get("/v1/query/{query_id}")
    def get_query(query_id: str):
        row = app.state.store.get_query(query_id)
        if row is None:
            raise HTTPException(status_code=404, detail="query not found")
        return {"query_id": query_id, **row}

    @app.post("/v1/feedback")
    def post_feedback(body: FeedbackRequest):
        from api.feedback import apply_feedback
        if app.state.store.get_query(body.query_id) is None:
            raise HTTPException(status_code=404, detail="query not found")
        apply_feedback(app.state.store, body.query_id, body.rating, body.note, settings)
        return {"status": "ok", "query_id": body.query_id, "rating": body.rating}

    return app


def _error(exc) -> dict:
    return {"error": {"code": type(exc).__name__, "message": str(exc)}}
