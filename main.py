from . import rest_endpoints
from cat.mad_hatter.decorators import hook, tool
from langchain.docstore.document import Document
from cat.log import log
import os, json, glob
import re
import cheshire_cat_api as ccat
import time

agent_response = ""
agent_why = None

# plugin default settings
lang = "English"
shared_data = ""
show_why = True

template_message_en = """
    You are an orchestrator of agents.
    Your task is to identify which agent is the most suitable to respond to the user’s message. You will be provided with the user’s message and a JSON list of the available agents.
    You must analyze the available agents and, based on the field agent_description, identify which agent is the most appropriate to answer the message.
    
    User message: 
    {message}

    List of agents in JSON format:
    {json_agents}

    Reply with a JSON containing the following information about the suitable agents:
        •	agent_name
        •	agent_url
        •	agent_port
        •	agent_key
        •	agent_ssl

    If there are no suitable agents, respond with an empty JSON.

    Your response must be a JSON without explanation, only agent details.

    Remove all markdown formatting.
    """


template_message_it = """
    Sei un orchestratore di agenti.
    Il tuo compito è identificare quale agente sia il più adatto a rispondere al messaggio dell’utente. Ti verrà fornito il messaggio dell’utente e un elenco in formato JSON degli agenti disponibili.
    Devi analizzare gli agenti disponibili e, basandoti sul campo agent_description, identificare quale agente è il più appropriato per rispondere al messaggio.

    Messaggio dell’utente:
    {message}

    Elenco degli agenti in formato JSON:
    {json_agents}

    Rispondi con un JSON contenente le seguenti informazioni riguardo l’agente idoneo:
    • agent_name
    • agent_url
    • agent_port
    • agent_key
    • agent_ssl

    Se non ci sono agenti idonei, rispondi con un JSON vuoto.

    La tua risposta deve essere un JSON senza spiegazioni, solo i dettagli dell’agente.

    Rimuovi tutta la formattazione markdown.
    """


@hook(priority=1)
def before_cat_reads_message(user_message_json, cat):
    global shared_data, show_why
    settings = cat.mad_hatter.get_plugin().load_settings()
    shared_data = settings["shared_data"]
    show_why = settings["show_agent_why"]
    if "shared_data" in user_message_json:
        shared_data = user_message_json.shared_data
    return user_message_json


@hook(priority=99)
def agent_fast_reply(fast_reply, cat):
    global lang
    settings = cat.mad_hatter.get_plugin().load_settings()
    lang = settings["language"]
    if lang == "English":
        template_message = template_message_en
    elif lang == "Italian":
        template_message = template_message_it
    user_message = cat.working_memory.user_message_json.text
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    agents_list = []
    if os.path.isdir(agents_dir):
        for path in glob.glob(os.path.join(agents_dir, "*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    agents_list.extend(data)
                else:
                    agents_list.append(data)
            except Exception:
                # skip unreadable or invalid files
                continue

    available_agents = json.dumps(agents_list, ensure_ascii=False)

    response = cat.llm(
        template_message.format(message=user_message, json_agents=available_agents)
    )
    # Rimuovi eventuale formattazione markdown (alcuni llm locali potrebbero includerla)
    response_clean = response
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", response, re.DOTALL)
    if match:
        response_clean = match.group(1)
    # Rimuovi eventuali caratteri markdown residui
    response_clean = response_clean.strip()
    # Estrai agent_name dal JSON di risposta
    try:
        response_json = json.loads(response_clean)
        selected_agent = response_json.get("agent_name", "") if response_json else ""
    except Exception:
        selected_agent = ""
    cat.working_memory.selected_agent = selected_agent

    if selected_agent != "":
        # Invia messaggio all'agente selezionato
        agent_response = send_message_to_agent(
            response_json, cat.working_memory.user_message_json.text, cat
        )
        fast_reply["output"] = agent_response

    return fast_reply


@hook
def before_cat_sends_message(msg, cat):
    global agent_why
    why = cat._StrayCat__build_why()
    why.selected_agent = cat.working_memory.selected_agent
    why.shared_data = shared_data
    why.agent_why = agent_why
    msg.why = why
    return msg


def send_message_to_agent(agent_data, msg, cat):
    global agent_response, shared_data, lang
    config = ccat.Config(
        user_id=cat.user_id,
        base_url=agent_data.get("agent_url", ""),
        port=agent_data.get("agent_port", 0),
        auth_key=agent_data.get("agent_key", ""),
        secure_connection=agent_data.get("agent_ssl", False),
    )
    cat_client = ccat.CatClient(config=config, on_message=agent_message_handler)

    # Connect to the WebSocket API
    cat_client.connect_ws()

    iterations = 1
    while not cat_client.is_ws_connected and iterations < 10:
        iterations += 1
        time.sleep(1)

    if iterations >= 10:
        return "Error: unable to connect to the selected agent."

    if shared_data is not None and shared_data != "" and lang == "English":
        msg = msg + "\n\nAdditional Information:\n" + shared_data

    if shared_data is not None and shared_data != "" and lang == "Italian":
        msg = msg + "\n\nInformazioni Aggiuntive:\n" + shared_data

    # Send the message
    cat_client.send(message=msg)

    while agent_response == "":
        time.sleep(1)

    # Close connection
    cat_client.close()
    return agent_response


def agent_message_handler(message: str):
    global agent_response, agent_why, show_why
    try:
        if isinstance(message, str):
            parsed = json.loads(message)
        else:
            parsed = message
    except Exception:
        parsed = None
        log.error(f"Error parsing message: {message}")
    if parsed["type"] == "chat":
        agent_response = parsed["content"]
        if show_why:
            agent_why = parsed["why"]


@hook(priority=99)
def before_rabbithole_insert_memory(doc: Document, cat) -> Document:
    doc.metadata["agent"] = "orchestrator"
    return doc


@hook(priority=99)
def before_cat_recalls_declarative_memories(
    declarative_recall_config: dict, cat
) -> dict:
    declarative_recall_config["metadata"] = {"agent": "orchestrator"}

    return declarative_recall_config
