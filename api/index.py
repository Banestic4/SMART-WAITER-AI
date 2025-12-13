from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from agents.smart_waiter_agent import SmartWaiterAgent
from config import Config

app = FastAPI()

# Security Scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == Config.APP_API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

# Initialize Agent
agent = SmartWaiterAgent()

@app.get("/")
def read_root():
    return {"message": "Smart Waiter API is running"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest, api_key: str = Depends(get_api_key)):
    try:
        response = agent.run(request.message, session_id=request.session_id)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import UploadFile, File
from groq import Groq
import os

# Initialize Groq Client for Audio
groq_client = Groq(api_key=Config.GROQ_API_KEY)

@app.post("/api/voice")
async def voice_endpoint(file: UploadFile = File(...), session_id: str = "default", api_key: str = Depends(get_api_key)):
    try:
        # Transcribe
        # Groq API requires file-like object with a name
        # We read the uploaded file into memory (fine for short voice clips)
        content = await file.read()
        
        # Determine format based on extension or default to .m4a/.wav 
        # (Groq supports flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, webm)
        filename = file.filename or "audio.m4a"
        
        transcription = groq_client.audio.transcriptions.create(
            file=(filename, content),
            model="whisper-large-v3", # Multilingual model
            response_format="text"
        )
        
        # Process text with Agent
        response_text = agent.run(transcription, session_id=session_id)
        
        return {
            "transcription": transcription,
            "response": response_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice Error: {str(e)}")
