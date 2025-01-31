from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
import logging
from bose_soundtouch import BoseClient, NowPlaying, Volume
from typing import Optional
import os
import httpx

logger = logging.getLogger(__name__)

app = FastAPI(title="Bose SoundTouch API")

# Create a shared httpx client for the proxy
http_client = httpx.AsyncClient()

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory containing api.py
current_dir = os.path.dirname(os.path.realpath(__file__))

index_path = os.path.join(current_dir, "index.html")
script_js_path = os.path.join(current_dir, "script.js")
styles_path = os.path.join(current_dir, "styles.css")

@app.get("/")
async def root():
    """Serve the index.html file"""
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)

@app.get("/script.js")
async def script_js():
    """Serve the script.js file"""
    if not os.path.exists(script_js_path):
        raise HTTPException(status_code=404, detail="script.js not found")
    return FileResponse(script_js_path, media_type="application/javascript")

@app.get("/styles.css")
async def styles():
    """Serve the styles.css file"""
    if not os.path.exists(styles_path):
        raise HTTPException(status_code=404, detail="styles.css not found")
    return FileResponse(styles_path, media_type="text/css")

# Pydantic models for request/response
class VolumeRequest(BaseModel):
    value: int = Field(..., ge=0, le=100)

class PresetRequest(BaseModel):
    value: int = Field(..., ge=1, le=6)

class DeviceConfig(BaseModel):
    hostname: str

# Store device configuration
device_config: Optional[DeviceConfig] = None

async def get_client() -> BoseClient:
    if device_config is None:
        raise HTTPException(status_code=400, detail="Device not configured")
    return BoseClient(device_config.hostname)

@app.post("/device/configure")
async def configure_device(config: DeviceConfig):
    """Configure the Bose device with hostname/IP"""
    global device_config
    device_config = config
    return {"message": "Device configured successfully"}

@app.get("/device/status")
async def get_status() -> NowPlaying:
    """Get the current playback status"""
    async with await get_client() as client:
        return await client.get_status()

@app.get("/device/volume")
async def get_volume() -> Volume:
    """Get the current volume"""
    async with await get_client() as client:
        return await client.get_volume()

@app.post("/device/volume")
async def set_volume(volume: VolumeRequest):
    """Set the volume (0-100)"""
    async with await get_client() as client:
        await client.set_volume(volume.value)
        return {"message": f"Volume set to {volume.value}"}

@app.post("/device/power")
async def toggle_power():
    """Toggle power state"""
    async with await get_client() as client:
        await client.power()
        return {"message": "Power toggled"}

@app.post("/device/play")
async def play():
    """Start playback"""
    async with await get_client() as client:
        await client.play()
        return {"message": "Playback started"}

@app.post("/device/pause")
async def pause():
    """Pause playback"""
    async with await get_client() as client:
        await client.pause()
        return {"message": "Playback paused"}

@app.post("/device/preset")
async def set_preset(preset: PresetRequest):
    """Select a preset (1-6)"""
    async with await get_client() as client:
        await client.set_preset(preset.value)
        return {"message": f"Selected preset {preset.value}"}

@app.get("/proxy/image")
async def proxy_image(url: str):
    """Proxy for container art images"""
    try:
        response = await http_client.get(url)
        response.raise_for_status()
        return Response(
            content=response.content,
            media_type=response.headers.get("content-type", "image/jpeg")
        )
    except httpx.HTTPError as e:
        logger.error(f"Error proxying image {url}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    uvicorn.run(app, host="0.0.0.0", port=8000) 