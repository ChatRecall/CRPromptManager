# cp_core.py

prompt_types = ["user", "system"]
prompt_subtypes = ['summary', 'evaluate', 'query']

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."
DEFAULT_AI_MODEL = "llama-3.1-405b"

DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0
DEFAULT_MAX_COMPLETION_TOKENS = 256

DEFAULT_VENICE_PARAMS = {}
