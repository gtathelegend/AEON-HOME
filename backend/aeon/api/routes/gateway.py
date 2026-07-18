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
    
    serial_writer = websocket.app.state.serial_writer
    sensor_processor = websocket.app.state.sensor_processor
    event_processor = websocket.app.state.event_processor
    
    # Register this websocket with the SerialWriter so PolicyEngine can send commands back
    serial_writer.attach(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            log.info("gateway.received", data=data)
            try:
                payload = json.loads(data)
                typ = payload.get("typ")
                
                if typ == "sensor_update":
                    # Reconstruct FeatureFrame
                    frame = FeatureFrame.from_json(payload)
                    # Simulate serial bridge counting frames
                    if hasattr(websocket.app.state, "serial_bridge") and websocket.app.state.serial_bridge:
                        websocket.app.state.serial_bridge._frames_parsed += 1
                        
                    asyncio.create_task(sensor_processor.on_feature_frame(frame))
                    
                elif typ in ["memory_status", "feedback_event", "heartbeat", "model_ack", "policy_ack"]:
                    event = AeonEvent.from_json(payload)
                    asyncio.create_task(event_processor.on_event(event))
                    
            except json.JSONDecodeError:
                log.warning("gateway.invalid_json", data=data)
            except Exception as e:
                log.exception("gateway.process_error", error=str(e))
                
    except WebSocketDisconnect:
        log.info("gateway.device_disconnected", client=websocket.client)
    finally:
        serial_writer.detach(websocket)

@router.websocket("/ws/dashboard")
async def dashboard_gateway(websocket: WebSocket):
    await websocket.accept()
    log.info("gateway.dashboard_connected", client=websocket.client)
    ws_bus = websocket.app.state.ws_bus
    await ws_bus.register_client(websocket)
