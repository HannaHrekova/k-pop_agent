from kpop_agent import process_dialogflow_request
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import json

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
CORS(app)

@app.route("/", methods=["POST"])
def webhook():
    logging.debug("Webhook function entered. Attempting to process request.") 

    fulfillment_text = "Sorry, something went wrong with the K-pop agent. Please try again later."
    status_code = 500

    try:
        req = request.get_json(silent=True, force=True)
        logging.debug(f"Dialogflow Request JSON received: {json.dumps(req, indent=2)}") 

        user_message = req.get("queryResult", {}).get("queryText")
        if not user_message:
            user_message = req.get("textInput", {}).get("query")

        if not user_message:
            logging.error("Could not parse user_message from Dialogflow request. Request body:") 
            logging.error(json.dumps(req, indent=2))
            fulfillment_text = "Sorry, I couldn't understand your request (no user message found)."
            status_code = 400
        else:
            fulfillment_text = process_dialogflow_request(user_message)
            status_code = 200

    except Exception as e:
        logging.error(f"Unhandled exception in webhook: {str(e)}")
        fulfillment_text = f"Sorry, there was an internal server error: {str(e)}"
        status_code = 500
    finally:
        return jsonify({"fulfillmentText": fulfillment_text}), status_code

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logging.info(f"Starting Flask app on port {port}...") 
    app.run(debug=False, host="0.0.0.0", port=port)

