import os
import requests
from datetime import datetime, timedelta, UTC
from dotenv import load_dotenv
import random # Not used in the provided code, but kept if it was intended for future use.

# --- Langchain and Hugging Face Imports ---
# These libraries are essential for working with the Large Language Model (LLM)
# and integrating external tools like web search and YouTube QA.
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import YouTubeSearchTool
from langchain_huggingface.chat_models import ChatHuggingFace
from langchain_huggingface.llms import HuggingFaceEndpoint
from pydantic import BaseModel, Field # Used for defining input schemas for tools.

# --- Environment Variable Loading ---
# Loads API keys from the .env file when running locally.
# On Render, these variables will be loaded from the service's environment settings.
load_dotenv()

# Check for the presence of the Hugging Face token. This is critical for the LLM to function.
hf_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
if not hf_token:
    print("CRITICAL ERROR: HUGGINGFACEHUB_API_TOKEN not loaded. Check .env file or Render settings.")
    # In a real webhook, you might want to return an error or log it more robustly.
    # For local testing, you might halt execution. On Render, the app should start,
    # but LLM calls will fail without the token.

# --- LLM Initialization ---
# Configures the Large Language Model from Hugging Face.
# repo_id: The identifier for the specific model being used (e.g., CohereLabs/c4ai-command-r-v01).
# huggingfacehub_api_token: Your personal token for accessing Hugging Face models.
# temperature: Controls the creativity/randomness of the model's output (lower = more predictable, higher = more varied).
# max_new_tokens: The maximum number of tokens the model will generate in its response.
llm_model = HuggingFaceEndpoint(
    repo_id="CohereLabs/c4ai-command-r-v01",
    huggingfacehub_api_token=hf_token, # Using the validated token
    # inference_server_url="https://api-inference.huggingface.co/models/", # Typically not needed for standard models
    # temperature=0.5, # Keep commented out for now
    # max_new_tokens=1024 # Keep commented out for now
)
chat = ChatHuggingFace(llm=llm_model)

# --- Tools ---
# These are the external functionalities that the LLM can call upon to gather information.

# 1. Web Search Tool (DuckDuckGo Search)
# Used for general internet searches.
class DuckDuckGoSearchInput(BaseModel):
    query: str = Field(description="The search query string for the internet.")

web_search_tool = DuckDuckGoSearchRun(
    name="web_search",
    description="Searches the web for general information, people, or topics. Always use a clear and concise search query.",
    args_schema=DuckDuckGoSearchInput
)

# 2. Youtube Video Q&A Tool
# Designed for answering specific questions about a given YouTube video URL.
# Our agent currently doesn't prompt the user for a URL, so this tool is used less frequently.
youtube_qa_tool = YouTubeSearchTool(
    name="youtube_video_qa",
    description="Useful for answering specific questions about a YouTube video. Input should be a JSON with 'url' (the video URL) and 'question' (the question about the video)."
)

# --- Your existing get_kpop_releases function ---
# This function specifically searches for new K-pop releases on YouTube.
# Note: In-memory caching (like `cached_result`) is not effective for stateless environments
# like Render's web services, where each request might run in a new instance.
# For persistent caching, a database or external store would be needed.
def get_kpop_releases(limit=10, search_period_days=7, filter_by_official_channels=True):
    API_KEY = os.getenv("YOUTUBE_API_KEY")
    if not API_KEY:
        # Returns a specific marker that the LLM can interpret as an API error
        return "youtube_api_error: YouTube API key is missing."

    url = "https://www.googleapis.com/youtube/v3/search"
    now = datetime.now(UTC)
    published_after_date = (now - timedelta(days=search_period_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "part": "snippet",
        # Broadened query for better detection of K-pop MVs
        "q": "K-pop official music video | K-pop comeback | K-pop debut | K-pop new song",
        "type": "video",
        "maxResults": limit,
        "order": "date",
        "publishedAfter": published_after_date,
        "videoCategoryId": "10", # Music category ID
        "key": API_KEY,
    }

    # List of official K-pop channels for filtering
    official_kpop_channels = [
        "HYBE LABELS", "JYP Entertainment", "SMTOWN", "YG Entertainment",
        "STAYC Official", "KQ ENTERTAINMENT", "PLEDIS Entertainment",
        "RBW Official", "SOURCE MUSIC", "CUBE Entertainment", "BANGTANTV",
        "BLACKPINK", "officialpsy", "1theK Originals"
    ]
    # Keywords to exclude unwanted content (e.g., reactions, covers)
    exclude_keywords = ["reaction", "cover", "fanmade", "edit", "lyrics", "compilation", "unboxing", "dance practice", "short"]

    try:
        response = requests.get(url, params=params, timeout=10) # Increased timeout for robustness
        response.raise_for_status() # Raises HTTPError for bad statuses (4xx, 5xx)
        data = response.json()

        if not data.get("items"):
            return "no_youtube_results_found" # Marker for the LLM

        releases = []
        for item in data["items"]:
            video_id = item["id"].get("videoId")
            if not video_id:
                continue

            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            link = f"https://www.youtube.com/watch?v={video_id}" # Standard YouTube link format

            title_lower = title.lower()
            channel_lower = channel.lower()

            is_spam_or_unwanted = False
            for keyword in exclude_keywords:
                if keyword in title_lower or keyword in channel_lower:
                    is_spam_or_unwanted = True
                    break

            # Filtering logic: if filtering by official channels OR (if not filtering, then only check for unwanted keywords)
            if (filter_by_official_channels and channel in official_kpop_channels and not is_spam_or_unwanted) or \
               (not filter_by_official_channels and not is_spam_or_unwanted):
                releases.append(f"{title} → {link}")
                if len(releases) >= 15: # Limits the number of results returned to the LLM
                    break

        if not releases:
            return "no_youtube_results_found"
        else:
            # Returns the list of releases in a format easily processable by the LLM
            return "YouTube Releases:\n" + "\n".join(releases)

    except requests.exceptions.RequestException as e:
        return f"youtube_api_error: {str(e)}" # Returns an error marker
    except Exception as e:
        return f"general_youtube_error: {str(e)}" # Returns a general error marker

# --- Main function for processing requests from Dialogflow ---
# This function takes the user's query, decides which tool to use,
# executes it, and returns the final response.
def process_dialogflow_request(user_message: str):
    # Initializes the message list, starting with the system prompt for the LLM.
    # This prompt instructs the LLM on its behavior and how to use the tools.
    messages_to_process = [SystemMessage(content="""
    You are a personal AI assistant named Jisoo, specializing exclusively in K-pop news and releases. Your goal is to answer user queries accurately and efficiently by using the available tools.

    You have access to the following tools:

    1.  **`get_kpop_releases_tool`**:
        * **Use this ONLY when the user explicitly asks for "new", "latest", or "recent" K-pop **music videos** or **MV releases** from **YouTube**.
        * **Input parameters**: `search_period_days` (int, default 7), `limit` (int, default 10), `filter_by_official_channels` (bool, default True).
        * **Example**: If the user says "Show new K-pop MVs from last month", you should call `get_kpop_releases_tool(search_period_days=30, limit=10)`.
        * If this tool returns "no_youtube_results_found", tell the user "Sorry, I couldn't find any new K-pop releases for the specified period on YouTube."

    2.  **`web_search`**:
        * **Use this for ALL other K-pop related queries that are NOT about new YouTube music videos.** This includes:
            * General K-pop news, comeback announcements, debut information.
            * Questions about specific groups or artists (e.g., "Tell me about BTS's latest activities", "When is BLACKPINK's next comeback?").
            * Questions about future releases or general K-pop trends.
            * Any K-pop query where `get_kpop_releases_tool` is not suitable.
        * **Input parameter**: `query` (string).
        * **Example**: If the user asks "What is new with BTS?", you should call `web_search(query='BTS latest news and activities')`.
        * **Always specify a timeframe (e.g., "this month", "today", "last week") in your search query if the user asks for "new" or "latest" information (unless it's an MV, then use `get_kpop_releases_tool`).**

    3.  **`youtube_video_qa`**:
        * **Use this ONLY if the user asks a very specific question ABOUT A GIVEN YOUTUBE VIDEO URL.** For example, "What is this video about: [URL]?".
        * **Input parameters**: `url` (string), `question` (string).

    **General Rules:**
    * You must always provide a concise and helpful summary of the results from the tools.
    * If a tool returns an error (like 'youtube_api_error', 'general_youtube_error', or 'web_search_error'), apologize and state that there was an issue retrieving information.
    * If you can't find information using your tools for K-pop queries, or if the question is not related to K-pop, you say: "Sorry, I couldn't find this information using my current tools or this question is outside my K-pop specialization."
    * Never make up information.
    """)]
    # Appends the user's message to the dialogue history.
    messages_to_process.append(HumanMessage(content=user_message))

    # --- Create a Langchain Tool for our get_kpop_releases function ---
    # This is necessary for the LLM to "see" and call our function as a tool.
    class GetKpopReleasesInput(BaseModel):
        limit: int = Field(default=10, description="Maximum number of results to return.")
        search_period_days: int = Field(default=7, description="Number of days back to search for releases.")
        filter_by_official_channels: bool = Field(default=True, description="Whether to filter by official K-pop channels.")

    get_kpop_releases_tool = Tool(
        name="get_kpop_releases_tool",
        description="Searches for new K-pop music videos and releases on YouTube.",
        func=get_kpop_releases,
        args_schema=GetKpopReleasesInput # Using the explicitly defined schema
    )

    # --- Bind the LLM with all available tools ---
    # The LLM will use these definitions to decide which tool to call.
    all_tools = [web_search_tool, youtube_qa_tool, get_kpop_releases_tool]
    chat_with_tools = chat.bind_tools(all_tools)

    # --- First LLM invocation ---
    # The LLM analyzes the user's query and the system prompt,
    # and decides whether to call a tool or respond directly.
    try:
        ai_message = chat_with_tools.invoke(messages_to_process)
    except Exception as e:
        print(f"ERROR: LLM invocation failed: {str(e)}")
        return "Sorry, I'm having trouble with my brain right now. Please try again later."


    # --- Processing LLM's response ---
    if ai_message.tool_calls:
        # If the LLM decided to call one or more tools
        tool_call = ai_message.tool_calls[0] # For simplicity, we take the first tool call
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_output = None
        
        print(f"DEBUG: LLM requested tool: {tool_name} with args: {tool_args}") # For debugging purposes

        # Execute the corresponding tool
        if tool_name == "get_kpop_releases_tool":
            tool_output = get_kpop_releases(**tool_args)
        elif tool_name == "web_search":
            tool_output = web_search_tool.invoke(tool_args["query"])
        elif tool_name == "youtube_video_qa":
            # youtube_qa_tool expects a dictionary with 'url' and 'question'
            tool_output = youtube_qa_tool.invoke(tool_args)
        else:
            return "Sorry, I tried to use an unknown tool."

        print(f"DEBUG: Tool '{tool_name}' output: {tool_output}") # For debugging purposes

        # Pass the tool's execution result back to the LLM,
        # so it can formulate a final, understandable response.
        # We use ToolMessage for the correct format.
        final_response_messages = messages_to_process + [
            ai_message, # The initial LLM message about the tool call
            ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]) # The tool's result
        ]
        
        try:
            final_ai_message = chat.invoke(final_response_messages)
            return final_ai_message.content
        except Exception as e:
            print(f"ERROR: Final LLM invocation after tool failed: {str(e)}")
            # Handle specific error markers from our tools
            if "no_youtube_results_found" in str(tool_output):
                return "Sorry, I couldn't find any new K-pop releases for the specified period on YouTube."
            elif "youtube_api_error" in str(tool_output) or "general_youtube_error" in str(tool_output):
                return "Sorry, I encountered an issue with the YouTube API. Please try again later."
            elif "web_search_error" in str(tool_output): # Assuming web_search_tool might also return errors
                return "Sorry, I had trouble performing a web search. Please try again later."
            else:
                return "Sorry, I processed the information, but I'm having trouble formulating a clear answer right now."
    else:
        # If the LLM responded without calling a tool (e.g., general knowledge, or refusal)
        return ai_message.content

