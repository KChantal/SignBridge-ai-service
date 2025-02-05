from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TextInput(BaseModel):
    text: str
    
@app.get("/")
def home():
    return {"home": "Welcome to the Python backend"}

@app.get("/health")
def health_check():
    return {"status": "running", "message": "Python AI service is up!"}

@app.post("/translate-to-sign")
async def translate_to_sign(data: TextInput):
    # TODO - add actual logic here later
    return {"sign": f"Text translated to sign: {data.text}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
