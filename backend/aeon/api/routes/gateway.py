from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
import json
import asyncio

from shared.types import FeatureFrame, AeonEvent

router = APIRouter(tags=["gateway"])
log = structlog.get_logger(__name__)

@router.websocket("/ws/device")
async def device_gateway(websocket: WebSocket):
    await websocket.accept()
    log.info("gateway.device_connected", client=websocket.client)
    
    gateway = websocket.app.state.communication_gateway
    serial_writer = websocket.app.state.serial_writer
    
    # Register connection in unified gateway
    await gateway.register_connection(websocket)
    # Register this websocket with the SerialWriter so PolicyEngine can send commands back
    serial_writer.attach(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            log.info("gateway.received", data=data)
            await gateway.handle_incoming(data, websocket)
                
    except WebSocketDisconnect:
        log.info("gateway.device_disconnected", client=websocket.client)
    finally:
        await gateway.deregister_connection(websocket)
        serial_writer.detach(websocket)

@router.websocket("/ws/dashboard")
async def dashboard_gateway(websocket: WebSocket):
    await websocket.accept()
    log.info("gateway.dashboard_connected", client=websocket.client)
    ws_bus = websocket.app.state.ws_bus
    await ws_bus.register_client(websocket)
