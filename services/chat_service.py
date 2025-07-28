import os
import requests
import datetime
import uuid
import json
import random
from utils.env_manager import get_llm_client
from utils.utils import get_history, store_history
from utils.constants import CITY_REQUEST_MESSAGES, SUCCESS_MESSAGES, DISABILITY_TYPES


def process_user_query(user_query: str, phone: str, user_location: str):
    llm = get_llm_client()
    history = get_history(phone)
    history_pairs = history[-2:] if len(history) >= 1 else history
    history_text = ""
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

    # Add intent classification
    intent_prompt = (
        f"Given a chat history and user query, classify the intent into one of these categories:\n"
        f"1. service_request: Query about services available in TAN network (e.g., asking about disability services, locations, providers)\n"
        f"2. bot_intent: Questions about the bot itself, what it does, how it works\n"
        f"3. out_of_scope: Any other queries\n\n"
        f"Return ONLY ONE of these exact values: service_request, bot_intent, or out_of_scope."
    )
    intent_prompt += f"User Query: {reformulated_query}\n"

    intent_response = llm.invoke(intent_prompt)
    intent = intent_response.content.strip().lower()
    print(f"Classified intent: {intent}")

    # Handle different intents
    if intent == "bot_intent":
        bot_info_prompt = (
            "You are The Ability Network (TAN) bot. Respond to the user's question about what you are or what you can do.\n"
            "Key information about you:\n"
            "- You are designed to help find disability support services across India\n"
            "- You can locate service providers based on disability type and location\n"
            "- You support multiple disability types including: Cerebral Palsy, Hearing Impairment, Intellectual Disability, etc.\n"
            "- Users need to specify both disability type and city to get the best results\n"
            "- You are part of The Ability Network (TAN) initiative by Tech Mahindra Foundation\n\n"
            f"User Query: {reformulated_query}\n"
            "Provide a concise response explaining who you are and how you can help, based on the user's specific question."
        )
        bot_info_response = llm.invoke(bot_info_prompt)
        bot_info = bot_info_response.content.strip()
        store_history(phone, reformulated_query, bot_info)
        return {"formatted_text": bot_info, "user_location": user_location}
    
    elif intent == "out_of_scope":
        out_of_scope_msg = (
            "Sorry, your query is out of knowledge. I'm specialized in helping you find disability support services. "
            "Please ask me about available services for different types of disabilities in your city."
        )
        store_history(phone, reformulated_query, out_of_scope_msg)
        return {"formatted_text": out_of_scope_msg, "user_location": user_location}

    # Continue with service request processing
    prompt = (
        f"You are an assistant. Given the following user query, identify the user's disability type and city. "
        f"Map the disability type to one of these: {', '.join(DISABILITY_TYPES)}. "
        f"If you are not able to identify the disability type, or cityreturn 'unknown'. "
        f"Return only two comma separated values: `disability_type,city`."
        f"Return ONLY ONE disability type and city in your response."
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
    
    if location == "unknown" and user_location != "unknown":
        location = user_location
    elif location != "unknown":
        user_location = location
    else:
        city_request = random.choice(CITY_REQUEST_MESSAGES)
        store_history(phone, reformulated_query, city_request)
        return {"formatted_text": city_request, "user_location": user_location}

    if disability_type == "unknown":
        disability_type = ""


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

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(SEARCH_URL, headers=headers, data=json.dumps(payload))
        print(f"response: {response}")
        
        response.raise_for_status()
        data = response.json()

        # Extract vendor details from the response
        result = []
        try:
            providers = data["message"]["catalog"]["message"]["catalog"]["providers"]
            if not providers:  # If providers list is empty
                no_services_msg = f"Sorry, I couldn't find any services for {disability_type} in {location}. Please try a different city or disability type."
                return {"formatted_text": no_services_msg, "vendors": []}

            # Limit to first 3 providers
            providers = providers[:3] if len(providers) > 3 else providers
            
            for provider in providers:
                vendor = {
                    "name": provider["descriptor"]["name"],
                    "branches": []
                }
                for loc in provider["locations"]:
                    if location.lower() in loc.get("address", "").lower():
                        # Get first contact from the contacts list if available
                        contact_info = loc.get("contacts", [])[0] if loc.get("contacts") else {}
                        vendor["branches"].append({
                            "branch name": loc.get("id", ""),
                            "address": loc.get("address", ""),    
                            "phone": contact_info.get("phone", ""),
                            "email": contact_info.get("email", ""),
                        })
                        result.append(vendor)

            if not result:  # If no matching locations found
                no_services_msg = f"Sorry, I couldn't find any services in {location}. Please try a different city or disability type."
                return {"formatted_text": no_services_msg, "vendors": [], "user_location": location}

            #take only top 5 vendors
            MAX_COUNT = 5
            formatted_result = ""
            for vendor in result:
                formatted_result += "*" + vendor["name"] + "*\n"
                for branch in vendor["branches"]:
                    formatted_result += "▪️" + branch["branch name"] + "\n  📍" + branch["address"]
                    if branch["phone"]:
                        formatted_result += "\n  📞" + branch["phone"]
                    if branch["email"]:
                        formatted_result += "\n  ✉️" + branch["email"]
                    formatted_result += "\n\n"
                    MAX_COUNT -= 1
                    if MAX_COUNT == 0:
                        break
                if MAX_COUNT == 0:
                    break

            # Add success message at the start
            success_msg = random.choice(SUCCESS_MESSAGES)
            formatted_result = success_msg + formatted_result
            print(f"formatted_result: {formatted_result}")

            return {
                "vendors": result,
                "formatted_text": formatted_result.strip(),
                "user_location": location
            }

        except KeyError as e:
            print(f"Error parsing vendor details - missing key: {e}")
            error_msg = f"Sorry, I couldn't find any services for {disability_type} in {location} at the moment. Please try again later."
            return {"formatted_text": error_msg, "vendors": [], "user_location": location}
            
        except Exception as e:
            print(f"Error parsing vendor details: {e}")
            error_msg = "I encountered an issue while processing the service information. Please try again later."
            return {"formatted_text": error_msg, "vendors": [], "user_location": location       }

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        error_msg = "I'm having trouble connecting to the service directory right now. Please try again in a few minutes."
        return {"formatted_text": error_msg, "vendors": [], "user_location": location} 