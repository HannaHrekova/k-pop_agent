### 🎧 K-pop Release Bot for Dialogflow

This is a simple chatbot webhook built with **Flask** that integrates with **Dialogflow** to return the latest K-pop music releases. It is a personal learning project and part of a hands-on exploration into AI agents, APIs, and chatbot development.

#### 🚀 Features

- Integrates with Dialogflow as a webhook
- Fetches recent K-pop releases (example dataset or dummy response)
- Built with Python, Flask, and requests
- Ready for deployment on Render or similar platforms

#### 🛠️ Tech Stack

- Python 3.10+
- Flask
- Flask-CORS
- Dialogflow (Google Cloud)
- Hosted on Render
- Environment variables managed via `.env`

#### 📁 Project Structure

-├── app.py # Main Flask app (Dialogflow webhook) 
-├── kpop_agent.py # Logic to fetch K-pop releases 
-├── requirements.txt # Required dependencies 
-├── .env # (Not included!) Holds API keys or configs 
-└── README.md

> ⚠️ `.env` is **not included** in the repository for security reasons. You must provide your own.

#### 📡 How It Works

Dialogflow sends a POST request to your Render-hosted endpoint. Based on the detected intent, the bot returns a list of new K-pop music releases.

#### 🧪 Example Dialogflow Intent

Intent Name: `Find Kpop Releases`  
Fulfillment: Webhook enabled  
Parameters: Optional parameter `limit` (number of releases)

#### 🔐 Security Notes

- **No API keys** or credentials are included in this repo.
- You must create a `.env` file locally or through your host (e.g., Render) with your configuration.
- Recommended: use `python-dotenv` to load `.env` files securely.

#### 📚 Status

📌 **Educational prototype in active development**  
I’m learning AI engineering and exploring how to build conversational agents. This is a sandbox for experimentation and creativity ✨

---

#### 📃 License

MIT License — feel free to fork and experiment, but attribution is appreciated 🙏

#### 🙋‍♀️ Author

This bot is developed and maintained by a passionate learner exploring AI, bots, and music tech.

