from flask import Flask, request, jsonify
from kpop_agent import get_kpop_releases

app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    intent = req["queryResult"]["intent"]["displayName"]

    if intent == "Find Kpop Releases":
        result = get_kpop_releases()
    else:
        result = "Sorry, I can't help you."

    return jsonify({"fulfillmentText": result})

if __name__ == "__main__":
    app.run(debug=True)
