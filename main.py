from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from uuid import uuid4
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage

# Import everything we need from sch2
from sch2 import graph, handle_smalltalk, appointments_collection

app = FastAPI(title="Appointment Scheduler API", version="1.0.0")

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

# In-memory session store
sessions: Dict[str, List[BaseMessage]] = {}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    user_input = req.message.strip()

    if session_id not in sessions:
        sessions[session_id] = []
    
    # Handle smalltalk
    smalltalk_response = handle_smalltalk(user_input)
    if smalltalk_response:
        return ChatResponse(response=smalltalk_response, session_id=session_id)
    
    # Update messages in session
    sessions[session_id].append(HumanMessage(content=user_input))
    
    try:
        # Invoke graph asynchronously
        result = await graph.ainvoke({"messages": sessions[session_id]})
        sessions[session_id] = result["messages"]
        
        final_text = None
        for msg in reversed(sessions[session_id]):
            if isinstance(msg, AIMessage) and msg.content:
                final_text = msg.content
                break
                
        response_text = final_text if final_text else "(no response)"
        return ChatResponse(response=response_text, session_id=session_id)
    except Exception as e:
        # Simple error handling
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/db")
async def get_db():
    cursor = appointments_collection.find({})
    records = await cursor.to_list(length=1000)
    for record in records:
        record["_id"] = str(record["_id"])
    return records

@app.get("/health")
async def health_check():
    return {"status": "ok"}
