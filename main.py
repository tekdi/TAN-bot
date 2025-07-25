from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.chat_service import process_user_query

app = FastAPI()

class ChatRequest(BaseModel):
    query: str
    phone: str

@app.post("/v1/chat")
def chat_endpoint(request: ChatRequest):
    try:
        print("1--")
        result = process_user_query(request.query, request.phone)
        print("2--")
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 