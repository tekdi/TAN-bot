import os
import requests
import datetime
import uuid
import json
from utils.env_manager import get_llm_client
from utils.utils import get_history, store_history

DISABILITY_TYPES = [
    "Intellectual Disability (ID)",
    "Hearing Impairment (HI)",
    "Multiple Disabilities",
    "Speech and Language disability",
    "Cerebral Palsy",
    "dwarfism",
    "Locomotor Disability",
    "Visual Impairment",

]

user_location=""
user_disability_type=""

def process_user_query(user_query: str, phone: str):
    global user_location
    global user_disability_type
    user_location = ""
    user_disability_type = ""
    print("1")
    llm = get_llm_client()
    print("2")
    history = get_history(phone)
    history_pairs = history[-2:] if len(history) >= 1 else history
    history_text = ""
    print("3")
    for pair in history_pairs:
        history_text += f"User: {pair['user']}\nAssistant: {pair['assistant']}\n"

    # First, reformulate the question if needed
    reformulation_prompt = (
        f"Given a chat history and the latest user question which might reference context in the chat history, "
        f"formulate a standalone question which can be understood without the chat history and that can be used to "
        f"find the most relevant documents. Do NOT answer the question, just reformulate it to a standalone question "
        f"if needed and otherwise return it as is.\n\n"
    )
    if history_text:
        reformulation_prompt += f"History:\n{history_text}\n"

    print(f"history_text: {history_text}")
    reformulation_prompt += f"Current Question: {user_query}\n"
    
    reformulated_response = llm.invoke(reformulation_prompt)
    reformulated_query = reformulated_response.content.strip()
    print(f"Original query: {user_query}")
    print(f"Reformulated query: {reformulated_query}")

    # Now use the reformulated query for the main prompt
    prompt = (
        f"You are an assistant. Given the following user query, identify the user's disability type and city. "
        f"Map the disability type to one of these: {', '.join(DISABILITY_TYPES)}. "
        f"If you are not able to identify the disability type, or cityreturn 'unknown'. "
        f"Return only two comma separated values: `disability_type,city`."
        f"Do not include any other text, country name or special characters in your response."
    )
    prompt += f"Current Query: {reformulated_query}\n"
    
    response = llm.invoke(prompt)
    try:
        disability_type, location = map(str.strip, response.content.split(",", 1))
        print(f"disability_type: {disability_type}, location: {location}")
    except Exception as e:
        print(e)
        raise ValueError("LLM response could not be parsed. Response: " + str(response))
    
    if location == "unknown" and user_location != "":
        location = user_location
    elif location != "unknown":
        user_location = location
    else:
        store_history(phone, reformulated_query, "Please provide your city")
        return {"formatted_text": "Please provide your city"}

    if disability_type != "unknown":
        user_disability_type = disability_type

    vendor_details = get_vendor_details(disability_type, location)
    # vendor_details = {"vendor_list": "vendor list sent"}

    store_history(phone, reformulated_query, "vendor list sent")
    return vendor_details


def get_vendor_details(disability_type: str, location: str):
    SEARCH_URL = os.getenv("SEARCH_URL")
    if not SEARCH_URL:
        raise ValueError("SEARCH_URL not set in environment variables")

    transaction_id = f"${uuid.uuid4()}"
    message_id = f"${uuid.uuid4()}"
    timestamp = (datetime.datetime.utcnow() + datetime.timedelta(days=365)).isoformat(timespec='milliseconds') + 'Z'

    payload = {
        "context": {
            "domain": "advisory:tan",
            "action": "search",
            "version": "1.1.0",
            "bap_id": "provider-tan-network.tekdinext.com",
            "bap_uri": "https://provider-tan-network.tekdinext.com",
            "transaction_id": transaction_id,
            "message_id": message_id,
            "timestamp": timestamp,
            "location": {
                "country": {
                    "code": "IND"
                }
            }
        },
        "message": {
            "intent": {
                "category": {
                    "descriptor": {
                        "code": "disability_services"
                    }
                },
                "item": {
                    "descriptor": {
                        "name": "Education"
                    }
                },
                "provider": {
                    "descriptor": {
                        "name": "Farrell Mcclure Trading"
                    }
                },
                "fulfillment": {
                    "end": {
                        "location": {
                            "gps": "",
                            "address": {
                                "city": location,
                                "area_code": "560001",
                                "country": "IND"
                            }
                        }
                    }
                },
                "tags": [
                    {
                        "code": "disability_type",
                        "list": [
                            {
                                "code": disability_type,
                                "value": disability_type
                            }
                        ]
                    }
                ]
            }
        }
    }

    print(f"payload: {payload}")

    headers = {"Content-Type": "application/json"}
    response = requests.post(SEARCH_URL, headers=headers, data=json.dumps(payload))

    print(f"response: {response}")
    
    response.raise_for_status()
    data = response.json()

    # Extract vendor details from the response
    result = []
    formatted_result = ""
    try:
        providers = data["message"]["catalog"]["message"]["catalog"]["providers"]
        # Limit to first 3 providers
        providers = providers[:3] if len(providers) > 3 else providers
        
        for provider in providers:
            vendor = {
                "name": provider["descriptor"]["name"],
                "branches": []
            }
            for loc in provider["locations"]:
                if location.lower() in loc.get("address", "").lower():
                    contacts = loc.get("contacts", {})
                    vendor["branches"].append({
                        "branch name": loc.get("id", ""),
                        "address": loc.get("address", ""),    
                        "phone": contacts.get("phone", ""),
                        "email": contacts.get("email", ""),
                    })
                    result.append(vendor)
        #take only top 5 vendors
        MAX_COUNT = 5
        for vendor in result:
            formatted_result += "*" + vendor["name"] + "*\n"
            for branch in vendor["branches"]:
                formatted_result += "▪️" + branch["branch name"] + "\n  📍" + branch["address"] + "\n  📞" + branch["phone"] + "\n  ✉️" + branch["email"] + "\n\n"
                MAX_COUNT -= 1
                if MAX_COUNT == 0:
                    break
            if MAX_COUNT == 0:
                break
        print(f"formatted_result: {formatted_result}")

    except Exception as e:
        print(f"Error parsing vendor details: {e}")
        return {"error": "Could not parse vendor details", "raw_response": data}

    return {
        "vendors": result,
        "formatted_text": formatted_result.strip()
    } 