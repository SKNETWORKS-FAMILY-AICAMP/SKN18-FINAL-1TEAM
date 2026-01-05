from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from graphs.listing_rag_graph import create_rag_graph
from common.redis_cache import get_search_context, save_search_context, get_accumulated_results, get_redis_client, save_conversation_turn
from pydantic import BaseModel
from typing import Optional
import uuid
import os
import logging
import sys
from pythonjsonlogger import jsonlogger

# =============================================================================
# JSON Logging Configuration (Requirements 5.2, 5.3)
# =============================================================================
def setup_json_logging():
    """Configure JSON-formatted logging for CloudWatch Logs compatibility."""
    log_format = os.getenv("LOG_FORMAT", "json")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format == "json":
        # JSON formatter for production (CloudWatch)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
            timestamp=True
        )
    else:
        # Standard formatter for development
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Configure uvicorn loggers to use the same format
    for uvicorn_logger in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uv_logger = logging.getLogger(uvicorn_logger)
        uv_logger.handlers = []
        uv_logger.addHandler(handler)
    
    return logger

# Initialize JSON logging
logger = setup_json_logging()

app = FastAPI(title="RAG System")

# =============================================================================
# CORS Configuration (Requirements 6.1)
# =============================================================================
# In production, CORS_ALLOWED_ORIGINS must be set via environment variable
# Format: comma-separated list of origins (e.g., "https://example.com,https://api.example.com")
# Default "*" is removed for security - must explicitly configure allowed origins
_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if _cors_origins_env:
    cors_origins = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
else:
    # Development defaults only - NOT for production
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check Endpoints for AWS ECS/ALB
# =============================================================================

@app.get("/health")
async def health():
    """
    Liveness probe endpoint.
    Returns 200 OK with {"status": "ok"} if the service is running.
    """
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """
    Readiness probe endpoint.
    Verifies Redis and Neo4j connectivity before returning 200 OK.
    Returns 503 Service Unavailable if any service is not connected.
    """
    status = {"status": "ok"}
    all_connected = True
    
    # Check Redis connectivity
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        status["redis"] = "connected"
    except Exception:
        status["redis"] = "disconnected"
        all_connected = False
    
    # Check Neo4j connectivity
    try:
        from langchain_community.graphs import Neo4jGraph
        graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            username=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )
        # Simple query to verify connection
        graph.query("RETURN 1")
        status["neo4j"] = "connected"
    except Exception:
        status["neo4j"] = "disconnected"
        all_connected = False
    
    if all_connected:
        return status
    else:
        status["status"] = "error"
        return JSONResponse(status_code=503, content=status)

graph = create_rag_graph()

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

@app.post("/query")
async def query(request: QueryRequest):
    # session_id 생성 또는 사용
    session_id = request.session_id or str(uuid.uuid4())
    
    # 1. 캐시된 검색 컨텍스트 로드
    search_context = get_search_context(session_id)
    cached_ids = search_context.get("property_ids", [])
    accumulated_results = search_context.get("accumulated_results", {})  # 누적된 모든 결과
    facility_types = search_context.get("facility_types", [])
    
    logger.info("RAG query received", extra={
        "question": request.question,
        "session_id": session_id[:8] + "...",
        "cached_ids_count": len(cached_ids),
        "accumulated_facilities": facility_types
    })
    
    # 2. RAG 그래프 호출 - 누적된 결과 전달
    result = await graph.ainvoke({
        "question": request.question,
        "session_id": session_id,
        "cached_property_ids": cached_ids,
        "accumulated_results": accumulated_results  # 누적된 모든 Q1+Q2+... 데이터
    })
    
    # 3. 결과 저장 (새 검색이든 캐시 사용이든 항상 누적)
    graph_results = result.get("graph_results", [])
    if graph_results:
        # ID 추출
        new_ids = []
        for r in graph_results:
            if isinstance(r, dict):
                prop_id = r.get("id") or r.get("p.id")
                if prop_id:
                    new_ids.append(str(prop_id))
        
        # 시설 타입 감지
        facility_type = detect_facility_type(request.question)
        
        # [DEBUG] 저장 전 필드 확인
        if graph_results:
            sample = graph_results[0] if isinstance(graph_results[0], dict) else {}
            sample_fields = [k for k in sample.keys() if sample.get(k)]
            logger.debug("Saving fields", extra={"fields": sample_fields[:10]})
        
        # 후속 질문이면 cache_filter에서 AND 필터링된 ID 사용
        filtered_ids = result.get("cached_property_ids", [])
        if filtered_ids:
            ids_to_save = filtered_ids[:20]  # cache_filter에서 AND 필터링된 결과
        elif cached_ids:
            ids_to_save = new_ids[:20] if new_ids else cached_ids[:20]
        else:
            ids_to_save = new_ids[:20]  # 첫 검색
        
        save_search_context(session_id, ids_to_save, facility_type, graph_results[:20])
        logger.info("Saved to cumulative cache", extra={"facility_type": facility_type})
    
    # 4. 대화 턴 저장 (최근 5개 유지)
    answer = result.get("answer", "")
    save_conversation_turn(session_id, request.question, answer)
    
    return {
        "answer": answer,
        "session_id": session_id
    }


def detect_facility_type(question: str) -> str:
    """질문에서 시설 타입 감지"""
    q = question.lower()
    facility_map = {
        "convenience": ["편의점", "마트", "gs25", "cu"],
        "hospital": ["병원", "의료", "종합병원"],
        "pharmacy": ["약국"],
        "park": ["공원", "산책"],
        "university": ["대학", "학교"],
        "subway": ["역", "지하철", "교통"],
        "safety": ["안전", "치안", "cctv", "경찰"]
    }
    for facility, keywords in facility_map.items():
        if any(kw in q for kw in keywords):
            return facility
    return "general"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
