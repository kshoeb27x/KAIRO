from backend.modules.google.calendar_intent import CalendarHandler
from backend.modules.google.gmail_intent import GmailHandler
from backend.modules.weather.weather_intent import WeatherHandler
from backend.modules.llm.chat_intent import ChatHandler
from backend.modules.research.research_intent import ResearchHandler
from backend.modules.rag.rag_intent import RAGHandler

# List all your handlers here
INTENT_HANDLERS = [
    CalendarHandler(),
    GmailHandler(),        
    ResearchHandler(),
    WeatherHandler(),
    RAGHandler(),
    ChatHandler(),
]