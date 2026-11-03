import pytest
from app.services.agent_service import AgentService, VoiceAgentSession

def test_slot_extraction_party_size_and_time():
    service = AgentService()
    session = VoiceAgentSession("test-slot-session")
    
    # Test 1: Complex sentence with party size and time with colon
    service._extract_contextual_slots(session, "Table for 4 tomorrow at 7:30 pm")
    assert session.slots["party_size"] == 4
    assert session.slots["time"] == "19:30"
    
    # Test 2: Modify to 6 people on the patio
    service._extract_contextual_slots(session, "Wait, make that 6 people on the patio instead!")
    assert session.slots["party_size"] == 6
    assert session.slots["seating_area"] == "patio"

def test_slot_extraction_allergens():
    service = AgentService()
    session = VoiceAgentSession("test-allergy-session")
    
    service._extract_contextual_slots(session, "I have a severe peanut and gluten allergy")
    assert "peanut" in session.slots["dietary_requirements"]
    assert "gluten" in session.slots["dietary_requirements"]

def test_slot_extraction_customer_details():
    service = AgentService()
    session = VoiceAgentSession("test-cust-session")
    
    session.last_prompt = "asking_name"
    service._extract_contextual_slots(session, "My name is John Doe")
    assert session.slots["customer_name"] == "John Doe"
    
    session.last_prompt = "asking_phone"
    service._extract_contextual_slots(session, "You can reach me at 555-432-1098")
    assert "555" in session.slots["customer_phone"]

