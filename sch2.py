# app.py
"""
One-file appointment scheduler / rescheduler / canceller
using LangChain + LangGraph + Ollama (llama3.1:latest)

Features:
- schedule appointment
- reschedule appointment
- cancel appointment
- check available slots for a date
- basic input validation
- conversation memory in the same CLI session
- MongoDB backend
- simple chit-chat handling for hi/hello/thanks/bye

Install:
    pip install -U langchain langgraph langchain-ollama motor

Run:
    ollama pull llama3.1:latest
    python app.py
"""

from __future__ import annotations

import os
import asyncio
from typing import Annotated, TypedDict, List, Dict
from uuid import uuid4
from datetime import datetime

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from motor.motor_asyncio import AsyncIOMotorClient


# ============================================================
# Database connection
# ============================================================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "scheduler_db")
client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]
appointments_collection = db.appointments

# ============================================================
# Helpers
# ============================================================

WORKING_HOURS = [
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
]


def is_valid_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_valid_time(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%H:%M")
        return time_str in WORKING_HOURS
    except ValueError:
        return False


def is_future_or_today(date_str: str) -> bool:
    target = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    return target >= today


async def appointment_exists(appointment_id: str) -> bool:
    appt = await appointments_collection.find_one({"appointment_id": appointment_id, "status": "scheduled"})
    return appt is not None


async def is_slot_available(date: str, time: str, exclude_appointment_id: str | None = None) -> bool:
    query = {"date": date, "time": time, "status": "scheduled"}
    if exclude_appointment_id:
        query["appointment_id"] = {"$ne": exclude_appointment_id}
    appt = await appointments_collection.find_one(query)
    return appt is None


async def get_available_slots(date: str) -> List[str]:
    available = []
    for slot in WORKING_HOURS:
        if await is_slot_available(date, slot):
            available.append(slot)
    return available


def format_appointment(record: Dict) -> str:
    return (
        f"appointment_id={record['appointment_id']}, "
        f"customer_name={record['customer_name']}, "
        f"date={record['date']}, time={record['time']}, "
        f"reason={record['reason']}, status={record['status']}"
    )


def handle_smalltalk(user_input: str) -> str | None:
    text = user_input.strip().lower()

    greetings = {"hi", "hello", "hey", "hi there", "hello there"}
    thanks = {"thanks", "thank you", "thx", "thanks a lot"}
    byes = {"bye", "goodbye", "see you", "see ya"}

    if text in greetings:
        return "Hello! I can help you schedule, reschedule, cancel appointments, or check available slots."

    if text in thanks:
        return "You're welcome!"

    if text in byes:
        return "Goodbye! Have a great day."

    return None


# ============================================================
# Tools
# ============================================================

@tool
async def schedule_appointment(customer_name: str, date: str, time: str, reason: str) -> str:
    """Schedule a new appointment."""
    if not customer_name.strip():
        return "FAILED: customer_name is required."

    if not is_valid_date(date):
        return "FAILED: date must be in YYYY-MM-DD format."

    if not is_future_or_today(date):
        return "FAILED: date cannot be in the past."

    if not is_valid_time(time):
        return f"FAILED: time must be one of {WORKING_HOURS}."

    if not reason.strip():
        return "FAILED: reason is required."

    if not await is_slot_available(date, time):
        alt = await get_available_slots(date)
        if alt:
            return f"FAILED: Slot {date} {time} is not available. Available slots on {date}: {', '.join(alt)}"
        return f"FAILED: Slot {date} {time} is not available and no slots are free on {date}."

    appointment_id = f"apt-{str(uuid4())[:8]}"
    record = {
        "appointment_id": appointment_id,
        "customer_name": customer_name,
        "date": date,
        "time": time,
        "reason": reason,
        "status": "scheduled",
    }
    
    await appointments_collection.insert_one(record)

    return "SUCCESS: " + format_appointment(record)


@tool
async def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> str:
    """Reschedule an existing appointment."""
    if not await appointment_exists(appointment_id):
        return f"FAILED: appointment {appointment_id} not found."

    if not is_valid_date(new_date):
        return "FAILED: new_date must be in YYYY-MM-DD format."

    if not is_future_or_today(new_date):
        return "FAILED: new_date cannot be in the past."

    if not is_valid_time(new_time):
        return f"FAILED: new_time must be one of {WORKING_HOURS}."

    if not await is_slot_available(new_date, new_time, exclude_appointment_id=appointment_id):
        alt = await get_available_slots(new_date)
        if alt:
            return f"FAILED: Slot {new_date} {new_time} is not available. Available slots on {new_date}: {', '.join(alt)}"
        return f"FAILED: Slot {new_date} {new_time} is not available and no slots are free on {new_date}."

    await appointments_collection.update_one(
        {"appointment_id": appointment_id},
        {"$set": {"date": new_date, "time": new_time}}
    )
    
    appt = await appointments_collection.find_one({"appointment_id": appointment_id})
    return "SUCCESS: " + format_appointment(appt)


@tool
async def cancel_appointment(appointment_id: str) -> str:
    """Cancel an existing appointment."""
    if not await appointment_exists(appointment_id):
        return f"FAILED: appointment {appointment_id} not found."

    await appointments_collection.update_one(
        {"appointment_id": appointment_id},
        {"$set": {"status": "cancelled"}}
    )
    
    appt = await appointments_collection.find_one({"appointment_id": appointment_id})
    return "SUCCESS: " + format_appointment(appt)


@tool
async def check_available_slots(date: str) -> str:
    """Check available appointment slots for a given date."""
    if not is_valid_date(date):
        return "FAILED: date must be in YYYY-MM-DD format."

    if not is_future_or_today(date):
        return "FAILED: date cannot be in the past."

    slots = await get_available_slots(date)
    if not slots:
        return f"SUCCESS: No slots available on {date}."
    return f"SUCCESS: Available slots on {date}: {', '.join(slots)}"


@tool
async def find_appointment_by_customer(customer_name: str) -> str:
    """Find scheduled appointments by customer name."""
    cursor = appointments_collection.find({
        "status": "scheduled", 
        "customer_name": {"$regex": f"^{customer_name}$", "$options": "i"}
    })
    matches = []
    async for record in cursor:
        matches.append(format_appointment(record))

    if not matches:
        return f"FAILED: no scheduled appointment found for customer_name={customer_name}"

    return "SUCCESS:\n" + "\n".join(matches)


tools = [
    schedule_appointment,
    reschedule_appointment,
    cancel_appointment,
    check_available_slots,
    find_appointment_by_customer,
]


# ============================================================
# LangGraph State
# ============================================================

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]


# ============================================================
# LLM
# ============================================================

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama3.1:latest"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=0,
)

llm_with_tools = llm.bind_tools(tools)


SYSTEM_PROMPT = """
You are a helpful appointment assistant.

Your responsibilities:
- Schedule appointments
- Reschedule appointments
- Cancel appointments
- Check available slots
- Help the user find an appointment by customer name

Rules:
- Use tools whenever an operation needs data lookup or update.
- If details are missing, ask only for the missing fields.
- For scheduling, collect: customer_name, date, time, reason
- For rescheduling, collect: appointment_id, new_date, new_time
- For cancellation, collect: appointment_id
- If the user does not know appointment_id, use find_appointment_by_customer
- Keep the final answer short and clear
- Do not invent appointment IDs
- If tool says FAILED, explain it naturally
- If the user is only doing casual chit-chat like greeting, thanking, or saying goodbye, respond naturally and do not call any tool
""".strip()


# ============================================================
# Nodes
# ============================================================

async def assistant_node(state: AgentState) -> AgentState:
    response = await llm_with_tools.ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    )
    return {"messages": [response]}


tool_node = ToolNode(tools)


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


# ============================================================
# Graph
# ============================================================

builder = StateGraph(AgentState)
builder.add_node("assistant", assistant_node)
builder.add_node("tools", tool_node)

builder.set_entry_point("assistant")
builder.add_conditional_edges("assistant", should_continue)
builder.add_edge("tools", "assistant")

graph = builder.compile()


# ============================================================
# CLI
# ============================================================

async def print_db() -> None:
    print("\nCurrent DB:")
    cursor = appointments_collection.find({})
    records = await cursor.to_list(length=100)
    
    if not records:
        print("  (empty)")
        return

    for record in records:
        # Convert ObjectId to string for easy reading, though not strictly required
        record.pop("_id", None)
        print(
            f"  {record['appointment_id']} | {record['customer_name']} | "
            f"{record['date']} {record['time']} | "
            f"{record['reason']} | {record['status']}"
        )


def print_examples() -> None:
    print("\nExamples:")
    print("  Hi")
    print("  Schedule an appointment for Amit on 2026-05-01 at 15:00 for general consultation")
    print("  What slots are available on 2026-05-01?")
    print("  Reschedule appointment apt-1001 to 2026-05-02 at 16:00")
    print("  Cancel appointment apt-1002")
    print("  Find Rahul's appointment")
    print("  Thank you")
    print("  Bye")


async def async_chat() -> None:
    print("Appointment Scheduler / Rescheduler / Canceller (MongoDB)")
    print("Type 'exit' to quit.")
    print_examples()
    await print_db()

    messages: List[BaseMessage] = []

    while True:
        # Note: input() is blocking, but it's fine for simple CLI
        user_input = input("\nYou: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("\nAssistant: Goodbye! Have a great day.")
            break

        # Handle chit-chat before LangGraph
        smalltalk_response = handle_smalltalk(user_input)
        if smalltalk_response:
            print("\nAssistant:", smalltalk_response)
            if user_input.strip().lower() in {"bye", "goodbye", "see you", "see ya"}:
                break
            continue

        messages.append(HumanMessage(content=user_input))

        result = await graph.ainvoke({"messages": messages})
        messages = result["messages"]

        final_text = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_text = msg.content
                break

        print("\nAssistant:", final_text if final_text else "(no response)")
        await print_db()

def chat() -> None:
    asyncio.run(async_chat())

if __name__ == "__main__":
    chat()