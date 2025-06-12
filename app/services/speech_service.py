"""
Speech processing service for real-time transcription
"""

import asyncio
import io
import logging
import tempfile
import time
from typing import Dict, Optional, Union

try:
    import openai
except ImportError:
    openai = None

try:
    import whisper
except ImportError:
    whisper = None

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

from ..config import get_settings

logger = logging.getLogger(__name__)

class SpeechService:
    """Service for handling speech-to-text operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.whisper_model = None
        
        # Initialize API clients
        self._init_openai()
        self._init_azure()
        
    def _init_openai(self):
        """Initialize OpenAI client"""
        if self.settings.OPENAI_API_KEY and openai:
            openai.api_key = self.settings.OPENAI_API_KEY
            logger.info("OpenAI client initialized")
    
    def _init_azure(self):
        """Initialize Azure Speech client"""
        if (self.settings.AZURE_SPEECH_KEY and 
            self.settings.AZURE_SPEECH_REGION and 
            speechsdk):
            self.azure_speech_config = speechsdk.SpeechConfig(
                subscription=self.settings.AZURE_SPEECH_KEY,
                region=self.settings.AZURE_SPEECH_REGION
            )
            self.azure_speech_config.speech_recognition_language = "en-GB"
            logger.info("Azure Speech client initialized")
    
    async def transcribe(self, audio_data: Union[bytes, str]) -> Dict:
        """Transcribe audio data to text"""
        try:
            engine = self.settings.SPEECH_RECOGNITION_ENGINE.lower()
            
            if engine == "openai" and openai:
                return await self._transcribe_openai(audio_data)
            elif engine == "azure" and speechsdk:
                return await self._transcribe_azure(audio_data)
            else:
                return await self._transcribe_whisper_local(audio_data)
                
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    async def _transcribe_openai(self, audio_data: Union[bytes, str]) -> Dict:
        """Transcribe using OpenAI Whisper API"""
        try:
            if isinstance(audio_data, bytes):
                audio_file = io.BytesIO(audio_data)
                audio_file.name = "audio.wav"
            else:
                audio_file = open(audio_data, "rb")
            
            # Updated for new OpenAI API
            client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
            transcript = await asyncio.to_thread(
                client.audio.transcriptions.create,
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
            
            return {
                "text": transcript.text,
                "confidence": 0.9,
                "language": getattr(transcript, 'language', 'en'),
                "duration": getattr(transcript, 'duration', 0)
            }
            
        except Exception as e:
            logger.error(f"OpenAI transcription error: {str(e)}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    async def _transcribe_whisper_local(self, audio_data: Union[bytes, str]) -> Dict:
        """Transcribe using local Whisper model"""
        try:
            if not whisper:
                return {"text": "", "confidence": 0.0, "error": "Whisper not installed"}
                
            if not self.whisper_model:
                self.whisper_model = whisper.load_model(self.settings.WHISPER_MODEL)
            
            if isinstance(audio_data, bytes):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                    temp_file.write(audio_data)
                    audio_path = temp_file.name
            else:
                audio_path = audio_data
            
            result = await asyncio.to_thread(
                self.whisper_model.transcribe,
                audio_path
            )
            
            return {
                "text": result["text"].strip(),
                "confidence": 0.85,
                "language": result["language"]
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {str(e)}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    async def _transcribe_azure(self, audio_data: Union[bytes, str]) -> Dict:
        """Transcribe using Azure Speech Services"""
        try:
            if not speechsdk:
                return {"text": "", "confidence": 0.0, "error": "Azure Speech SDK not installed"}
                
            if isinstance(audio_data, bytes):
                stream = speechsdk.audio.PushAudioInputStream()
                audio_config = speechsdk.audio.AudioConfig(stream=stream)
                stream.write(audio_data)
                stream.close()
            else:
                audio_config = speechsdk.audio.AudioConfig(filename=audio_data)
            
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.azure_speech_config,
                audio_config=audio_config
            )
            
            result = await asyncio.to_thread(speech_recognizer.recognize_once)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return {
                    "text": result.text,
                    "confidence": 0.9,
                    "language": "en-GB"
                }
            else:
                return {"text": "", "confidence": 0.0, "error": "No speech recognized"}
                
        except Exception as e:
            logger.error(f"Azure transcription error: {str(e)}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    async def transcribe_realtime(self, audio_chunk: bytes) -> Dict:
        """Transcribe audio chunk in real-time"""
        try:
            if not AudioSegment:
                # Fallback to basic transcription without audio processing
                return await self.transcribe(audio_chunk)
                
            audio_segment = AudioSegment.from_raw(
                io.BytesIO(audio_chunk),
                sample_width=2,
                frame_rate=self.settings.AUDIO_SAMPLE_RATE,
                channels=1
            )
            
            if len(audio_segment) < 500:
                return {"text": "", "confidence": 0.0, "is_final": False}
            
            if audio_segment.dBFS < -40:
                return {"text": "", "confidence": 0.0, "is_final": False}
            
            buffer = io.BytesIO()
            audio_segment.export(buffer, format="wav")
            audio_bytes = buffer.getvalue()
            
            result = await self._transcribe_whisper_local(audio_bytes)
            result["is_final"] = len(result.get("text", "")) > 0
            
            return result
            
        except Exception as e:
            logger.error(f"Real-time transcription error: {str(e)}")
            return {"text": "", "confidence": 0.0, "is_final": False, "error": str(e)}
    
    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return str(int(time.time() * 1000)) 