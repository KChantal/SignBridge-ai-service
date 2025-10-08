"""
Main FastAPI application for Here & Hear AI Service
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import List
import json

from .services.speech_service import SpeechService
from .services.websocket_manager import WebSocketManager
from .config import get_settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Here & Hear AI Service",
    description="AI-powered speech processing and BSL avatar generation service",
    version="0.1.0"
)

# CORS middleware for mobile app integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
settings = get_settings()
speech_service = SpeechService()
websocket_manager = WebSocketManager()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Here & Hear AI Service is running", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "speech_processing": "ready"
        }
    }

@app.post("/transcribe")
async def transcribe_audio(audio_data: dict):
    """
    Transcribe audio to text
    """
    try:
        # Extract audio data from request
        audio_file = audio_data.get("audio")
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio data provided")
        
        # Process audio through speech service
        transcription = await speech_service.transcribe(audio_file)
        
        return {
            "transcription": transcription,
            "timestamp": speech_service.get_timestamp(),
            "confidence": transcription.get("confidence", 0.0),
            "language": "en-GB"
        }
    
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcription failed")

@app.websocket("/ws/live-transcription")
async def websocket_live_transcription(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech transcription
    """
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Receive audio data from client
            data = await websocket.receive_bytes()
            
            # Process audio in real-time
            transcription = await speech_service.transcribe_realtime(data)
            
            # Send transcription back to client
            await websocket_manager.send_personal_message(
                json.dumps({
                    "type": "transcription",
                    "text": transcription.get("text", ""),
                    "confidence": transcription.get("confidence", 0.0),
                    "is_final": transcription.get("is_final", False),
                    "language": "en-GB"
                }),
                websocket
            )
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("Client disconnected from live transcription")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 