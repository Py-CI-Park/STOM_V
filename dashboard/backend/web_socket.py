
import asyncio
import pandas as pd
from typing import Dict, List
from fastapi import WebSocket
from database import DatabaseManager


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}  # {market: {client_id: websocket}}
        self.active_tasks: Dict[str, bool] = {}  # {market: task_running}
        self.task_refs: Dict[str, asyncio.Task] = {}  # {market: task_reference}
        self.db = DatabaseManager()

    async def connect(self, websocket: WebSocket, client_id: str, market: str):
        await websocket.accept()
        if market not in self.active_connections:
            self.active_connections[market] = {}
        self.active_connections[market][client_id] = websocket

        # 연결 직후 즉시 데이터 전송
        await self.send_initial_data(websocket, market)

        # 해당 거래소의 태스크가 실행 중이 아니면 시작
        if market not in self.active_tasks or not self.active_tasks[market]:
            self.active_tasks[market] = True
            task = asyncio.create_task(self.broadcast_data(market))
            self.task_refs[market] = task

    async def send_initial_data(self, websocket: WebSocket, market: str):
        """연결 직후 즉시 데이터 전송"""
        try:
            tradelist = self.db.get_tradelist(market)
            totaltradelist = self.db.get_totaltradelist(market)

            # 당일데이터 필터링하여 거래횟수 계산
            if totaltradelist and tradelist:
                today = pd.Timestamp.now()
                today_str = f"{today.year}{str(today.month).zfill(2)}{str(today.day).zfill(2)}"
                today_trades = [trade for trade in tradelist if trade.get("체결시간") and str(trade["체결시간"])[:8] == today_str]
                totaltradelist["거래횟수"] = len(today_trades)

            data = {
                "jangolist": self.db.get_jangolist(market),
                "chegeollist": self.db.get_chegeollist(market),
                "tradelist": tradelist,
                "totaltradelist": totaltradelist,
                "timestamp": pd.Timestamp.now().isoformat()
            }

            alerts = self.check_alerts(data["jangolist"])
            if alerts:
                data["alerts"] = alerts

            await websocket.send_json(data)
        except Exception as e:
            print(f"Initial data transmission error: {e}")

    def disconnect(self, client_id: str, market: str):
        if market in self.active_connections and client_id in self.active_connections[market]:
            del self.active_connections[market][client_id]
            if not self.active_connections[market]:
                del self.active_connections[market]
                self.active_tasks[market] = False  # 연결이 없으면 태스크 중단 플래그 설정
                # 태스크 즉시 중단
                if market in self.task_refs and self.task_refs[market]:
                    self.task_refs[market].cancel()
                    del self.task_refs[market]

    async def broadcast_data(self, market: str = "stock"):
        while True:
            try:
                tradelist = self.db.get_tradelist(market)
                totaltradelist = self.db.get_totaltradelist(market)

                # 당일데이터 필터링하여 거래횟수 계산
                if totaltradelist and tradelist:
                    today = pd.Timestamp.now()
                    today_str = f"{today.year}{str(today.month).zfill(2)}{str(today.day).zfill(2)}"
                    today_trades = [trade for trade in tradelist if trade.get("체결시간") and str(trade["체결시간"])[:8] == today_str]
                    totaltradelist["거래횟수"] = len(today_trades)

                data = {
                    "jangolist": self.db.get_jangolist(market),
                    "chegeollist": self.db.get_chegeollist(market),
                    "tradelist": tradelist,
                    "totaltradelist": totaltradelist,
                    "timestamp": pd.Timestamp.now().isoformat()
                }

                alerts = self.check_alerts(data["jangolist"])
                if alerts:
                    data["alerts"] = alerts

                # 해당 거래소에 연결된 클라이언트에게만 데이터 전송
                if market in self.active_connections:
                    for connection in self.active_connections[market].values():
                        try:
                            await connection.send_json(data)
                        except Exception as e:
                            print(f"Data transmission error: {e}")

                await asyncio.sleep(1)
            except Exception as e:
                print(f"Broadcast error: {e}")
                await asyncio.sleep(1)

    def check_alerts(self, jangolist: List[dict]) -> List[dict]:
        alerts = []
        for item in jangolist:
            if item.get("수익률", 0) > 5.0:
                alerts.append({
                    "type": "profit",
                    "message": f"{item['종목명']} profit rate {item['수익률']:.2f}% reached",
                    "stock": item['종목명']
                })
            elif item.get("수익률", 0) < -3.0:
                alerts.append({
                    "type": "loss",
                    "message": f"{item['종목명']} loss rate {item['수익률']:.2f}% reached",
                    "stock": item['종목명']
                })
        return alerts
