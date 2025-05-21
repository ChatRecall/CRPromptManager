# cp_core.py
import logging

# Logger Configuration
logger = logging.getLogger(__name__)

from WrapAI import VeniceModels

# Constants and Values
prompt_roles = ["user", "system"]
prompt_subtypes = ['summary', 'evaluate', 'query']

PROMPT_TYPE_QUESTION = "question"
PROMPT_TYPE_CHAT = "chat"
PROMPT_TYPES = [PROMPT_TYPE_QUESTION, PROMPT_TYPE_CHAT]

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI assistant."

SECRETS_FILE_NAME = ".env"
API_KEY_NAME = "Venice_API_KEY"
DEFAULT_AI_MODEL = "venice-uncensored"

DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0
DEFAULT_FREQUENCY_PENALTY = 0.0
DEFAULT_PRESENCE_PENALTY = 0.0
DEFAULT_MAX_COMPLETION_TOKENS = 256

DEFAULT_VENICE_PARAMS = {}

# Composite key names for runtime storage
MODEL_ATTRIBUTES_FULL = "model_attributes_full"
MODEL_ATTRIBUTES_STRING = "model_attributes_string"

def display_label(ptype: str) -> str:
    return ptype.capitalize()

# Helper functions
def populate_runtime_models(api_key, run_time, refresh=False):
    """
    Loads and stores the full detail dict in runtime.
    Returns the full_dict.
    """
    full = run_time.get_runtime_variable(MODEL_ATTRIBUTES_FULL)
    if refresh or not full:
        venice_models = VeniceModels(api_key)
        venice_models.fetch_models()
        full = venice_models.get_full_model_detail_dict()
        run_time.add_runtime_variable(MODEL_ATTRIBUTES_FULL, full)
        logger.info(f"Model details stored: {len(full)} models")
    return full

def get_available_models(api_key, run_time, refresh=False):
    # Only get the full dict now
    full_dict = populate_runtime_models(api_key, run_time, refresh=refresh)
    model_list = sorted(full_dict)
    # Build the display dict here for UI, as needed
    display_dict = {}
    for model_id, model in full_dict.items():
        spec = model.get("model_spec", {})
        caps = spec.get("capabilities", {})
        tokens = spec.get("availableContextTokens", "N/A")
        reasoning = caps.get("supportsReasoning", False)
        schema = caps.get("supportsResponseSchema", False)
        web = caps.get("supportsWebSearch", False)
        display_dict[model_id] = (
            f"tokens: {tokens}, reasoning: {reasoning}, response_schema: {schema}, web_search: {web}"
        )
    return model_list, full_dict, display_dict

def populate_model_combo_list(model_combobox, current_model, api_key, run_time, refresh=False):
    model_list, _, display_dict = get_available_models(api_key, run_time, refresh=refresh)
    model_combobox.clear()
    for model in model_list:
        display = f"{model} ({display_dict.get(model, '')})"
        model_combobox.addItem(display, model)

    if current_model in model_list:
        model_combobox.setCurrentIndex(model_list.index(current_model))
    else:
        model_combobox.setCurrentIndex(0)

def get_model_attributes(model_name, api_key, run_time, refresh=False):
    """
    Returns the full attribute dictionary for a given model.
    """
    full_dict = populate_runtime_models(api_key, run_time, refresh=refresh)
    return full_dict.get(model_name, {})

