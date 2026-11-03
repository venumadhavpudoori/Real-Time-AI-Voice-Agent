import re
import json
import asyncio
import datetime
from datetime import date, time, timedelta
from typing import Dict, Any, Optional, List, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.agent import AgentStateEnum, WebSocketMessageType, ServerMessage
from app.guardrails import safety_pipeline
from app.services.tool_registry import (
    TOOLS_METADATA,
    check_table_availability,
    create_reservation,
    check_dietary_safety,
    cancel_reservation,
    get_menu_recommendations,
    parse_date_str,
    parse_time_str
)
from app.services.tts_service import tts_service


class VoiceAgentSession:
    """Manages dialogue state, context, slot-filling, and interruption handling for a live voice call."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = AgentStateEnum.IDLE
        self.history: List[Dict[str, str]] = []
        self.last_prompt: Optional[str] = None  # 'asking_name', 'asking_phone', 'asking_party_size', 'asking_time'
        self.slots = {
            "customer_name": None,
            "customer_phone": None,
            "party_size": None,
            "date": None,
            "time": None,
            "seating_area": "indoor",
            "dietary_requirements": None,
            "allergy_level": "NONE",
            "special_requests": None
        }
        self.active_task: Optional[asyncio.Task] = None
        self.is_interrupted = False

    def reset(self):
        self.state = AgentStateEnum.IDLE
        self.history.clear()
        self.last_prompt = None
        self.slots = {
            "customer_name": None,
            "customer_phone": None,
            "party_size": None,
            "date": None,
            "time": None,
            "seating_area": "indoor",
            "dietary_requirements": None,
            "allergy_level": "NONE",
            "special_requests": None
        }
        self.is_interrupted = False


class AgentService:
    """Core Voice Agent coordinating speech-to-text input, safety guardrails, SQL tools, and TTS."""

    def __init__(self):
        self.sessions: Dict[str, VoiceAgentSession] = {}

    def get_session(self, session_id: str) -> VoiceAgentSession:
        if session_id not in self.sessions:
            self.sessions[session_id] = VoiceAgentSession(session_id)
        return self.sessions[session_id]

    async def handle_interruption(
        self,
        session_id: str,
        emit_func: Callable[[ServerMessage], Any],
        db: Optional[AsyncSession] = None
    ):
        """Immediately interrupts speech output and resets agent to LISTENING state."""
        session = self.get_session(session_id)
        session.is_interrupted = True

        if session.active_task and not session.active_task.done():
            session.active_task.cancel()

        session.state = AgentStateEnum.INTERRUPTED
        await emit_func(ServerMessage(
            type=WebSocketMessageType.INTERRUPT,
            state=AgentStateEnum.INTERRUPTED,
            text="User barged in. Audio output halted.",
            metadata={"reason": "User speech detected during agent playback"}
        ))

        # Log interruption event
        await safety_pipeline.log_interruption(db, stage="playback", details="User speech barge-in")

        # Ready for user input
        session.state = AgentStateEnum.LISTENING
        await emit_func(ServerMessage(
            type=WebSocketMessageType.STATE_CHANGE,
            state=AgentStateEnum.LISTENING,
            text="Listening..."
        ))

    async def process_user_speech(
        self,
        session_id: str,
        raw_text: str,
        emit_func: Callable[[ServerMessage], Any],
        db: AsyncSession
    ):
        """Processes user voice transcript through guardrails, tool calls, and dialogue generation."""
        session = self.get_session(session_id)
        session.is_interrupted = False

        if not raw_text or not raw_text.strip():
            return

        # 1. State: THINKING
        session.state = AgentStateEnum.THINKING
        await emit_func(ServerMessage(
            type=WebSocketMessageType.STATE_CHANGE,
            state=AgentStateEnum.THINKING,
            text="Processing speech..."
        ))

        # 2. Safety Guardrails Pipeline
        guardrail_result = await safety_pipeline.process_input(raw_text, db=db)
        sanitized_text = guardrail_result["processed_text"]

        # Notify frontend of any triggered guardrail events
        if guardrail_result["guardrail_events"]:
            for event in guardrail_result["guardrail_events"]:
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.GUARDRAIL_TRIGGERED,
                    guardrail_info=event,
                    text=f"Guardrail triggered: {event['type']} (Risk: {event['risk']})"
                ))

        # Check if input was blocked by prompt safety
        if guardrail_result["is_blocked"]:
            await self._speak(session, guardrail_result["processed_text"], emit_func)
            return

        # Append to conversation history
        session.history.append({"role": "user", "content": sanitized_text})

        # Check for interruption before proceeding
        if session.is_interrupted:
            return

        # 3. Process with OpenAI LLM (if configured) or Built-in Intelligent Dialogue Engine
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 10:
            await self._process_with_llm(session, sanitized_text, emit_func, db)
        else:
            await self._process_with_rules(session, sanitized_text, emit_func, db)

    async def _process_with_rules(
        self,
        session: VoiceAgentSession,
        user_text: str,
        emit_func: Callable[[ServerMessage], Any],
        db: AsyncSession
    ):
        """
        High-fidelity Built-in Natural Language Voice Agent Engine.
        Handles reservations, SQL tools, allergy checks, dietary requirements,
        cancellations, and interruptions with zero external dependencies.
        """
        text_lower = user_text.lower().strip()

        # Step 1: Contextual Slot Extraction based on previous prompt
        self._extract_contextual_slots(session, user_text)

        # Step 2: Handle Cancellation Intent
        if "cancel" in text_lower or (session.last_prompt == "asking_cancel_code" and "res-" in text_lower):
            code_match = re.search(r'\b(RES-[A-Z0-9]{4,8})\b', user_text, re.IGNORECASE)
            if code_match:
                code = code_match.group(1).upper()
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.TOOL_START,
                    state=AgentStateEnum.CALLING_TOOL,
                    tool_name="cancel_reservation",
                    tool_args={"confirmation_code": code}
                ))
                tool_res = await cancel_reservation(db, code)
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.TOOL_RESULT,
                    tool_name="cancel_reservation",
                    tool_result=tool_res
                ))
                session.last_prompt = None
                await self._speak(session, tool_res["message"], emit_func)
                return
            else:
                session.last_prompt = "asking_cancel_code"
                await self._speak(session, "To cancel your booking, could you please provide your reservation reference code, for example RES-DEMO01?", emit_func)
                return

        # Step 3: Handle Menu & Dietary Safety Query Intent
        menu_keywords = ["menu", "food", "dishes", "dish", "recommend", "eat", "serve", "allergy", "allergic", "vegan", "gluten", "nut free"]
        if any(w in text_lower for w in menu_keywords):
            # If user mentioned an allergy or dietary restriction
            if session.slots.get("dietary_requirements"):
                req = session.slots["dietary_requirements"]
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.TOOL_START,
                    state=AgentStateEnum.CALLING_TOOL,
                    tool_name="check_dietary_safety",
                    tool_args={"dietary_requirements": req}
                ))
                safety_report = await check_dietary_safety(db, req)
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.TOOL_RESULT,
                    tool_name="check_dietary_safety",
                    tool_result=safety_report
                ))

                safe_list = ", ".join(safety_report["safe_dishes"][:3])
                reply = f"For your {req} requirements, safe dishes include {safe_list}."
                if safety_report["unsafe_dishes"]:
                    flagged = ", ".join([d["dish_name"] for d in safety_report["unsafe_dishes"][:2]])
                    reply += f" Please avoid {flagged} as they contain conflicting allergens."
                reply += " Would you like me to check table availability to book for dinner?"
                await self._speak(session, reply, emit_func)
                return
            else:
                # General menu recommendation
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.TOOL_START,
                    state=AgentStateEnum.CALLING_TOOL,
                    tool_name="get_menu_recommendations",
                    tool_args={"category": "All"}
                ))
                menu_res = await get_menu_recommendations(db)
                await emit_func(ServerMessage(
                    type=WebSocketMessageType.TOOL_RESULT,
                    tool_name="get_menu_recommendations",
                    tool_result=menu_res
                ))
                top_dishes = [d["name"] for d in menu_res["dishes"][:3]]
                reply = f"Our chef recommends {', '.join(top_dishes)}. Do you have any dietary restrictions or would you like to book a table?"
                await self._speak(session, reply, emit_func)
                return

        # Step 4: Handle Availability & Booking Workflow
        slots = session.slots
        booking_keywords = [
            "book", "reserve", "table", "party", "reservation", "seats", "seat",
            "available", "availability", "tonight", "tomorrow", "friday", "saturday",
            "sunday", "dinner", "lunch", "make that", "change to", "switch to",
            "people", "guests", "patio", "outdoor", "indoor", "bar", "instead", "reschedule"
        ]
        has_booking_intent = (
            any(w in text_lower for w in booking_keywords) or 
            session.last_prompt in ("asking_name", "asking_phone", "asking_party_size", "asking_time")
        )

        # If user is in the middle of answering booking questions OR expresses booking intent
        if has_booking_intent:
            # Set default date and time if not yet chosen
            if not slots["date"]:
                slots["date"] = str(date.today() + timedelta(days=1))
            if not slots["time"]:
                slots["time"] = "19:00"

            p_size = slots["party_size"] or 2
            d_val = parse_date_str(slots["date"])
            t_val = parse_time_str(slots["time"])

            # 1. Ask for party size if missing
            if not slots["party_size"]:
                session.last_prompt = "asking_party_size"
                await self._speak(session, "How many guests will be joining for the reservation?", emit_func)
                return

            # 2. Check table availability via SQL
            await emit_func(ServerMessage(
                type=WebSocketMessageType.TOOL_START,
                state=AgentStateEnum.CALLING_TOOL,
                tool_name="check_table_availability",
                tool_args={
                    "date": slots["date"],
                    "time": slots["time"],
                    "party_size": p_size,
                    "seating_area": slots["seating_area"]
                }
            ))

            avail_res = await check_table_availability(db, d_val, t_val, p_size, slots["seating_area"])
            await emit_func(ServerMessage(
                type=WebSocketMessageType.TOOL_RESULT,
                tool_name="check_table_availability",
                tool_result=avail_res
            ))

            if not avail_res["available"]:
                session.last_prompt = "asking_time"
                await self._speak(session, avail_res["message"], emit_func)
                return

            # 3. If table is available, check for Customer Name
            if not slots["customer_name"]:
                session.last_prompt = "asking_name"
                table_name = avail_res["matched_table"]["table_number"]
                area_name = avail_res["matched_table"]["seating_area"]
                await self._speak(
                    session,
                    f"Table {table_name} in the {area_name} section is available for {p_size} guests on {d_val} at {t_val.strftime('%I:%M %p')}. May I please have your full name for the booking?",
                    emit_func
                )
                return

            # 4. Check for Phone Number
            if not slots["customer_phone"]:
                session.last_prompt = "asking_phone"
                await self._speak(
                    session,
                    f"Thank you, {slots['customer_name']}. What is your phone number to confirm your reservation?",
                    emit_func
                )
                return

            # 5. All slots filled -> Confirm booking via PostgreSQL SQL Tool!
            await emit_func(ServerMessage(
                type=WebSocketMessageType.TOOL_START,
                state=AgentStateEnum.CALLING_TOOL,
                tool_name="create_reservation",
                tool_args={
                    "customer_name": slots["customer_name"],
                    "customer_phone": slots["customer_phone"],
                    "party_size": p_size,
                    "date": str(d_val),
                    "time": t_val.strftime("%H:%M"),
                    "dietary_requirements": slots["dietary_requirements"]
                }
            ))

            booking_res = await create_reservation(
                db=db,
                customer_name=slots["customer_name"],
                customer_phone=slots["customer_phone"],
                date_val=d_val,
                time_val=t_val,
                party_size=p_size,
                seating_area=slots["seating_area"],
                dietary_requirements=slots["dietary_requirements"],
                special_requests=slots["special_requests"]
            )

            await emit_func(ServerMessage(
                type=WebSocketMessageType.TOOL_RESULT,
                tool_name="create_reservation",
                tool_result=booking_res
            ))

            # Speak confirmation and reset dialogue turn
            session.reset()
            await self._speak(session, booking_res["message"], emit_func)
            return

        # General Greeting / Help
        session.last_prompt = None
        greeting = (
            "Hello! Welcome to The Grand Bistro Voice Concierge. "
            "I can help you check table availability, book reservations, or check menu allergen safety. "
            "How can I help you today?"
        )
        await self._speak(session, greeting, emit_func)

    def _extract_contextual_slots(self, session: VoiceAgentSession, text: str):
        """Extracts slots like party size, date, time, customer name, phone, and dietary constraints."""
        text_lower = text.lower().strip()
        cleaned_words = [w.strip() for w in text.split() if w.strip()]

        # 1. If agent was waiting for customer name:
        if session.last_prompt == "asking_name" and not session.slots["customer_name"]:
            # Check for phrases like "my name is X", "this is X", or directly "First Last"
            name_match = re.search(r'\b(?:my name is|this is|i am|name is|it is|it\'s)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b', text, re.IGNORECASE)
            if name_match:
                session.slots["customer_name"] = name_match.group(1).title().strip()
            elif 1 <= len(cleaned_words) <= 3 and not any(char.isdigit() for char in text):
                # User simply stated their name: "Alice", "John Smith"
                candidate = " ".join(cleaned_words).title()
                if candidate.lower() not in ["yes", "no", "sure", "cancel", "ok", "hello", "hi", "patio", "table", "book"]:
                    session.slots["customer_name"] = candidate

        # 2. If agent was waiting for phone number:
        phone_match = re.search(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\d{7,11}\b', text)
        if phone_match:
            session.slots["customer_phone"] = phone_match.group(0).strip()
        elif session.last_prompt == "asking_phone" and not session.slots["customer_phone"]:
            # Extract consecutive digits
            digits = re.sub(r'\D', '', text)
            if len(digits) >= 7:
                session.slots["customer_phone"] = digits

        # 3. Party Size
        party_match = re.search(r'\b(?:make that|change to|party of|table for|for|seats?)\s+(\d{1,2})\b', text_lower)
        if party_match:
            session.slots["party_size"] = int(party_match.group(1))
        else:
            people_match = re.search(r'\b(\d{1,2})\s*(?:people|guests|persons|seats)\b', text_lower)
            if people_match:
                session.slots["party_size"] = int(people_match.group(1))
            else:
                word_numbers = {
                    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
                    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
                }
                for word, num in word_numbers.items():
                    if (f"table for {word}" in text_lower or 
                        f"party of {word}" in text_lower or 
                        f"{word} people" in text_lower or 
                        f"{word} guests" in text_lower or
                        f"make that {word}" in text_lower):
                        session.slots["party_size"] = num
                        break

        # If agent specifically asked for party size and user just said a number
        if session.last_prompt == "asking_party_size" and not session.slots["party_size"]:
            num_match = re.search(r'\b(\d{1,2})\b', text)
            if num_match:
                session.slots["party_size"] = int(num_match.group(1))

        # 4. Date
        today = date.today()
        if "today" in text_lower or "tonight" in text_lower:
            session.slots["date"] = str(today)
        elif "tomorrow" in text_lower:
            session.slots["date"] = str(today + timedelta(days=1))
        else:
            days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for idx, day_name in enumerate(days_of_week):
                if day_name in text_lower:
                    today_weekday = today.weekday()
                    days_ahead = (idx - today_weekday) % 7
                    if days_ahead == 0:
                        days_ahead = 7
                    session.slots["date"] = str(today + timedelta(days=days_ahead))
                    break
            if not session.slots["date"]:
                date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
                if date_match:
                    session.slots["date"] = date_match.group(1)

        # 5. Time (strict matching to avoid confusing party size numbers with hours)
        time_colon = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', text_lower)
        time_ampm = re.search(r'\b(\d{1,2})\s*(am|pm)\b', text_lower)
        time_at = re.search(r'\b(?:at|around)\s+(\d{1,2})\b', text_lower)

        if time_colon:
            hour = int(time_colon.group(1))
            minute = int(time_colon.group(2))
            meridiem = time_colon.group(3)
            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            elif not meridiem and hour < 11:
                # Default dinner hour e.g. 7:30 -> 19:30
                hour += 12
            session.slots["time"] = f"{hour:02d}:{minute:02d}"
        elif time_ampm:
            hour = int(time_ampm.group(1))
            meridiem = time_ampm.group(2)
            if meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
            session.slots["time"] = f"{hour:02d}:00"
        elif time_at:
            hour = int(time_at.group(1))
            if 1 <= hour <= 12:
                if hour < 11:
                    hour += 12
                session.slots["time"] = f"{hour:02d}:00"

        # 6. Dietary Requirements & Allergies
        allergy_keywords = ["peanut", "peanuts", "nut", "nuts", "gluten", "celiac", "dairy", "lactose", "shellfish", "vegan", "vegetarian", "halal", "kosher", "egg", "eggs", "soy", "fish"]
        found_allergens = [kw for kw in allergy_keywords if kw in text_lower]
        if found_allergens:
            session.slots["dietary_requirements"] = ", ".join(found_allergens)

        # 7. Seating Area
        if "patio" in text_lower or "outdoor" in text_lower or "outside" in text_lower or "terrace" in text_lower:
            session.slots["seating_area"] = "patio"
        elif "bar" in text_lower or "counter" in text_lower:
            session.slots["seating_area"] = "bar"
        elif "private" in text_lower or "private room" in text_lower:
            session.slots["seating_area"] = "private_room"
        elif "indoor" in text_lower or "inside" in text_lower or "main room" in text_lower:
            session.slots["seating_area"] = "indoor"
        elif "private" in text_lower:
            session.slots["seating_area"] = "private_room"

    async def _process_with_llm(
        self,
        session: VoiceAgentSession,
        user_text: str,
        emit_func: Callable[[ServerMessage], Any],
        db: AsyncSession
    ):
        """Processes query via OpenAI LLM with function calling if API key is provided."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an empathetic, articulate AI voice agent for The Grand Bistro restaurant. "
                        "You help guests book reservations, check table availability, inspect dietary requirements, "
                        "and handle cancellations. You must always prioritize food allergen safety guardrails. "
                        "Be concise (1-3 sentences) suitable for natural speech synthesis."
                    )
                }
            ] + session.history

            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                tools=TOOLS_METADATA,
                tool_choice="auto",
                temperature=0.7
            )

            response_msg = response.choices[0].message

            # Check if LLM requested a tool call
            if response_msg.tool_calls:
                for tool_call in response_msg.tool_calls:
                    fn_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments or "{}")

                    await emit_func(ServerMessage(
                        type=WebSocketMessageType.TOOL_START,
                        state=AgentStateEnum.CALLING_TOOL,
                        tool_name=fn_name,
                        tool_args=args
                    ))

                    # Execute SQL Tool
                    tool_result = await self._execute_tool(fn_name, args, db)
                    await emit_func(ServerMessage(
                        type=WebSocketMessageType.TOOL_RESULT,
                        tool_name=fn_name,
                        tool_result=tool_result
                    ))

                    # Send tool result back to LLM for final natural voice response
                    messages.append(response_msg)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                    followup = await client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=messages,
                        temperature=0.7
                    )
                    final_text = followup.choices[0].message.content or ""
                    await self._speak(session, final_text, emit_func)
            else:
                reply_text = response_msg.content or ""
                await self._speak(session, reply_text, emit_func)

        except Exception as exc:
            # Fallback gracefully to rule engine if OpenAI call fails
            await self._process_with_rules(session, user_text, emit_func, db)

    async def _execute_tool(self, name: str, args: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """Dispatches tool call to SQL integration functions."""
        if name == "check_table_availability":
            d_val = parse_date_str(args.get("date", str(date.today())))
            t_val = parse_time_str(args.get("time", "19:00"))
            p_size = int(args.get("party_size", 2))
            return await check_table_availability(db, d_val, t_val, p_size, args.get("seating_area"))
        elif name == "create_reservation":
            d_val = parse_date_str(args.get("date", str(date.today())))
            t_val = parse_time_str(args.get("time", "19:00"))
            return await create_reservation(
                db=db,
                customer_name=args.get("customer_name", "Guest"),
                customer_phone=args.get("customer_phone", "000-000-0000"),
                date_val=d_val,
                time_val=t_val,
                party_size=int(args.get("party_size", 2)),
                seating_area=args.get("seating_area", "indoor"),
                dietary_requirements=args.get("dietary_requirements"),
                special_requests=args.get("special_requests")
            )
        elif name == "check_dietary_safety":
            return await check_dietary_safety(
                db=db,
                dietary_requirements=args.get("dietary_requirements", ""),
                dish_names=args.get("dish_names")
            )
        elif name == "cancel_reservation":
            return await cancel_reservation(
                db=db,
                confirmation_code=args.get("confirmation_code", ""),
                customer_phone=args.get("customer_phone")
            )
        elif name == "get_menu_recommendations":
            return await get_menu_recommendations(
                db=db,
                dietary_requirements=args.get("dietary_requirements"),
                category=args.get("category")
            )
        return {"error": f"Unknown tool: {name}"}

    async def _speak(
        self,
        session: VoiceAgentSession,
        text: str,
        emit_func: Callable[[ServerMessage], Any]
    ):
        """Synthesizes voice audio non-blockingly and streams text and audio to client, honoring interruptions."""
        if session.is_interrupted:
            return

        session.state = AgentStateEnum.SPEAKING
        session.history.append({"role": "assistant", "content": text})

        # Synthesize audio base64 via TTS in background thread so event loop never stalls
        audio_b64 = await asyncio.to_thread(tts_service.synthesize_to_base64, text)

        await emit_func(ServerMessage(
            type=WebSocketMessageType.AGENT_RESPONSE,
            state=AgentStateEnum.SPEAKING,
            text=text,
            audio_base64=audio_b64 if audio_b64 else None
        ))


agent_service = AgentService()

__all__ = ["AgentService", "agent_service", "VoiceAgentSession"]
