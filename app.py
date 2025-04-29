from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from kpop_agent import get_kpop_releases

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["POST"])
def webhook():
    try:
        req = request.get_json(force=True)
        intent = req.get("queryResult", {}).get("intent", {}).get("displayName")

        if intent == "Find Kpop Releases":
            result = get_kpop_releases()
        else:
            result = "Sorry, I can't help you with that request."
            
    except Exception as e:
        result = f"Error processing the request: {str(e)}"

    return jsonify({"fulfillmentText": result})

if __name__ == "__main__":
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
