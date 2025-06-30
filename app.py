from kpop_agent import process_dialogflow_request
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

@app.route("/", methods=["POST"])
def webhook():
    print("DEBUG: Webhook function entered. Attempting to process request.")
    # Initialize fulfillment_text with a default error message
    fulfillment_text = "Sorry, something went wrong with the K-pop agent. Please try again later."
    status_code = 500 # Default to 500 Internal Server Error

    try:
        req = request.get_json(silent=True, force=True)
        print(f"Dialogflow Request: {json.dumps(req, indent=2)}")

        user_message = req.get("queryResult", {}).get("queryText")
        if not user_message:
            user_message = req.get("textInput", {}).get("query")

        if not user_message:
            print("ERROR: Could not parse user_message from Dialogflow request. Request body:")
            print(json.dumps(req, indent=2))
            fulfillment_text = "Sorry, I couldn't understand your request (no user message found)."
            status_code = 400 # Bad Request
            # No return here, let it fall through to the final jsonify

        else: # Only proceed if user_message was successfully extracted
            # Pass the user's message to the K-pop AI agent
            fulfillment_text = process_dialogflow_request(user_message)
            status_code = 200 # OK

    except Exception as e:
        print(f"ERROR: Unhandled exception in webhook: {str(e)}")
        # If an exception occurs, use the error message from the exception
        fulfillment_text = f"Sorry, there was an internal server error: {str(e)}"
        status_code = 500 # Ensure status code is 500 for unhandled exceptions

    finally: # This block will always execute before returning
        # Always return a JSON response with the fulfillmentText and appropriate status
        return jsonify({"fulfillmentText": fulfillment_text}), status_code

# This is common in Flask to run the app if the script is executed directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask app on port {port}...")
    app.run(debug=False, host="0.0.0.0", port=port)

