from kpop_agent import process_dialogflow_request
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["POST"])
def webhook():
    try:
        req = request.get_json(silent=True, force=True)
        print(f"Dialogflow Request: {json.dumps(req, indent=2)}")

        user_message = req.get("queryResult", {}).get("queryText") # For Dialogflow ES (V2) 
        if not user_message:
            user_message = req.get("textInput", {}).get("query") # For Dialogflow CX

        if not user_message:
            print("ERROR: Could not parse user_message from Dialogflow request. Request body:")
            print(json.dumps(req, indent=2))
            return jsonify({"fulfillmentText": "Sorry, I couldn't understand your request (no user message found)."}), 400 # Повертаємо 400 Bad Request

        # Passing the user request to the agent
        fulfillment_text = process_dialogflow_request(user_message)

    except Exception as e:
        print(f"ERROR: Unhandled exception in webhook: {str(e)}") # Logging an error
        fulfillment_text = f"Sorry, there was an internal error processing your request: {str(e)}"
        return jsonify({"fulfillmentText": fulfillment_text}), 500 # Return 500 Internal Server Error

    # Form an answer for Dialogflow
    # Dialogflow expects the "fulfillmentText" key for a simple text response
    fulfillment_response = {
        "fulfillmentText": fulfillment_text
    }
    print(f"Dialogflow Response: {json.dumps(fulfillment_response, indent=2)}")
    return jsonify(fulfillment_response)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting Flask app on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)

