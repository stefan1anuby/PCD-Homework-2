import functions_framework
import logging

# Define a dictionary of hateful words
HATEFUL_WORDS = {
    "hate", "racist", "stupid", "idiot", "dumb", "ugly", "kill", "nazi"
}

def contains_hate_speech(text):
    """Check if the text contains any hateful words."""
    words = set(text.lower().split())  # Convert text to lowercase and split into words
    return any(word in HATEFUL_WORDS for word in words)

@functions_framework.http
def check_offensive_message(request):
    try:
        request_json = request.get_json()

        if not request_json or "text" not in request_json:
            return {"error": "Missing 'text' parameter"}, 400

        text = request_json["text"]
        is_offensive = contains_hate_speech(text)

        return {"offensive": is_offensive}, 200

    except Exception as e:
        logging.error(f"Internal function error: {str(e)}")
        return {"error": "Internal server error", "details": str(e)}, 500