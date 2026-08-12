import os
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
import logging

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool, Tool
from langchain_community.tools import DuckDuckGoSearchRun, YouTubeSearchTool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_cohere import ChatCohere
from pydantic import BaseModel, Field

load_dotenv()

# --- LLM Initialization ---
cohere_api_key = os.environ.get("COHERE_API_KEY")
if not cohere_api_key:
    cohere_api_key = os.environ.get("HUGGINGFACEHUB_API_TOKEN")

chat = ChatCohere(
    model="command-r-08-2024",
    cohere_api_key=cohere_api_key,
    temperature=0.2,
    max_tokens=300
)
logging.debug("LLM (ChatCohere) initialized.")

# --- Base Tools ---
wrapper = DuckDuckGoSearchAPIWrapper(max_results=2)
_ddg_search = DuckDuckGoSearchRun(api_wrapper=wrapper)
_yt_search = YouTubeSearchTool()

@tool
def web_search(query: str) -> str:
    """Searches the web for general information, news, comebacks, or topics.
    Always use a clear search query string."""
    try:
        return _ddg_search.run(query)
    except Exception as e:
        return f"web_search_error: {str(e)}"

@tool
def youtube_video_qa(query: str) -> str:
    """Searches YouTube for official videos, music videos, or performances.
    Input should be a search query string."""
    try:
        return _yt_search.run(query)
    except Exception as e:
        return f"youtube_qa_error: {str(e)}"

# --- Custom YouTube API Function ---
def get_kpop_releases(limit=10, search_period_days=7, filter_by_official_channels=True):
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    if not API_KEY:
        return "youtube_api_error: YouTube API key is missing."

    url = "https://www.googleapis.com/youtube/v3/search"
    now = datetime.now(UTC)
    published_after_date = (now - timedelta(days=search_period_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "part": "snippet",
        "q": "K-pop official music video | K-pop comeback | K-pop debut | K-pop new song",
        "type": "video",
        "maxResults": limit,
        "order": "date",
        "publishedAfter": published_after_date,
        "videoCategoryId": "10",
        "key": API_KEY,
    }

    official_kpop_channels = [
        "HYBE LABELS", "JYP Entertainment", "SMTOWN", "YG Entertainment",
        "STAYC Official", "KQ ENTERTAINMENT", "PLEDIS Entertainment",
        "RBW Official", "SOURCE MUSIC", "CUBE Entertainment", "BANGTANTV",
        "BLACKPINK", "officialpsy", "1theK Originals"
    ]
    exclude_keywords = ["reaction", "cover", "fanmade", "edit", "lyrics", "compilation", "unboxing", "dance practice", "short"]

    try:
        response = requests.get(url, params=params, timeout=4)
        response.raise_for_status()
        data = response.json()

        if not data.get("items"):
            return "no_youtube_results_found"

        releases = []
        for item in data["items"]:
            video_id = item["id"].get("videoId")
            if not video_id:
                continue

            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            link = f"https://www.youtube.com/watch?v={video_id}"

            title_lower = title.lower()
            channel_lower = channel.lower()

            is_spam_or_unwanted = any(keyword in title_lower or keyword in channel_lower for keyword in exclude_keywords)

            if (filter_by_official_channels and channel in official_kpop_channels and not is_spam_or_unwanted) or \
               (not filter_by_official_channels and not is_spam_or_unwanted):
                releases.append(f"{title} → {link}")
                if len(releases) >= 15:
                    break

        if not releases:
            return "no_youtube_results_found"
        return "YouTube Releases:\n" + "\n".join(releases)

    except requests.exceptions.RequestException as e:
        return f"youtube_api_error: {str(e)}"
    except Exception as e:
        return f"general_youtube_error: {str(e)}"


class GetKpopReleasesInput(BaseModel):
    limit: int = Field(default=10, description="Maximum number of results to return.")
    search_period_days: int = Field(default=7, description="Number of days back to search for releases.")
    filter_by_official_channels: bool = Field(default=True, description="Whether to filter by official K-pop channels.")

get_kpop_releases_tool = Tool(
    name="get_kpop_releases_tool",
    description="Searches for new K-pop music videos and releases on YouTube.",
    func=get_kpop_releases,
    args_schema=GetKpopReleasesInput
)

# --- Dialogflow Request Handler ---
def process_dialogflow_request(user_message: str):
    logging.debug(f"DEBUG: process_dialogflow_request received user_message: '{user_message}'")
    
    current_date_str = datetime.now().strftime("%B %Y")
    current_year = datetime.now().year

    system_prompt = f"""You are a personal AI assistant named Jisoo, specializing exclusively in K-pop news and releases.

CRITICAL TIME CONTEXT: Current date is {current_date_str}. Always assume queries about "latest", "recent", "new", or "current" events refer to {current_year} unless specified otherwise.

You have access to the following tools:

1. **`get_kpop_releases_tool`**:
   - Use this ONLY when the user explicitly asks for "new", "latest", or "recent" K-pop music videos or MV releases from YouTube.
   - If it returns "no_youtube_results_found", state that no new releases were found for that period.

2. **`web_search`**:
   - Use this for ALL other K-pop news, comebacks, debuts, or general questions.
   - When searching for recent events, ALWAYS include the current year ({current_year}) or month in your query (e.g., "K-pop comebacks {current_date_str}").

3. **`youtube_video_qa`**:
   - Use this to search for specific YouTube videos or performances. Input must be a search string.

General Rules:
- Provide a concise and helpful summary.
- If the question is outside K-pop or no info is found, say: "Sorry, I couldn't find this information using my current tools or this question is outside my K-pop specialization."
- Never make up information.
"""

    messages_to_process = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ]

    all_tools = [web_search, youtube_video_qa, get_kpop_releases_tool]
    chat_with_tools = chat.bind_tools(all_tools)

    response = chat.invoke(messages_to_process)
    return response.content
    # try:
        # ai_message = chat_with_tools.invoke(messages_to_process)
        # logging.debug(f"DEBUG: AI's initial decision: {ai_message}")
    # except Exception as e:
       # logging.error(f"ERROR: LLM invocation failed: {str(e)}")
       # return "Sorry, I'm having trouble processing your request right now. Please try again later."

    if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
        tool_call = ai_message.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_output = None

        logging.debug(f"DEBUG: LLM requested tool: {tool_name} with args: {tool_args}")

        if tool_name == "get_kpop_releases_tool":
            tool_output = get_kpop_releases(**tool_args)
        elif tool_name == "web_search":
            tool_output = web_search.invoke(tool_args.get("query", ""))
        elif tool_name == "youtube_video_qa":
            tool_output = youtube_video_qa.invoke(tool_args.get("query", ""))
        else:
            return "Sorry, I tried to use an unknown tool."

        logging.debug(f"DEBUG: Tool '{tool_name}' output: {tool_output}")

        final_response_messages = messages_to_process + [
            ai_message,
            ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"])
        ]

        try:
            final_ai_message = chat.invoke(final_response_messages)
            logging.debug(f"DEBUG: Final AI message content: {final_ai_message.content}")
            return final_ai_message.content
        except Exception as e:
            logging.error(f"ERROR: Final LLM invocation failed: {str(e)}")
            if "no_youtube_results_found" in str(tool_output):
                return "Sorry, I couldn't find any new K-pop releases for the specified period on YouTube."
            return "Sorry, I processed the information, but I'm having trouble formulating a clear answer right now."
    else:
        return ai_message.content

