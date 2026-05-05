
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from web_socket import WebSocketManager


# 환경변수에서 마켓코드와 포트 읽기
STOM_MARKET_CODE = os.getenv('STOM_MARKET_CODE', 'stock')
STOM_BACKEND_PORT = int(os.getenv('STOM_BACKEND_PORT', '8000'))

app = FastAPI(title=f"STOM Trading Dashboard API - {STOM_MARKET_CODE}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ws_manager = WebSocketManager()


@app.get("/")
async def root():
    return {"message": f"STOM Trading Dashboard API - {STOM_MARKET_CODE}"}


@app.get("/api/market")
async def get_market_data():
    """고정된 마켓의 데이터를 반환합니다."""
    from database import DatabaseManager
    db = DatabaseManager()
    return {
        "jangolist": db.get_jangolist(STOM_MARKET_CODE),
        "chegeollist": db.get_chegeollist(STOM_MARKET_CODE),
        "tradelist": db.get_tradelist(STOM_MARKET_CODE),
        "totaltradelist": db.get_totaltradelist(STOM_MARKET_CODE)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """고정된 마켓용 WebSocket 엔드포인트."""
    client_id = str(uuid.uuid4())
    await ws_manager.connect(websocket, client_id, STOM_MARKET_CODE)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(client_id, STOM_MARKET_CODE)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(client_id, STOM_MARKET_CODE)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=STOM_BACKEND_PORT)
