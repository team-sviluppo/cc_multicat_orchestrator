import json
import os
from cat.log import log
from typing import List, Union, Dict
from cat.mad_hatter.decorators import endpoint
from cat.auth.permissions import AuthResource, AuthPermission, check_permissions
from pydantic import BaseModel


class AgentDetails(BaseModel):
    agent_name: str
    agent_description: str
    agent_url: str
    agent_port: int = None
    agent_ssl: bool
    agent_key: str


@endpoint.post(path="/register-agent", prefix="/multicat")
def agent_register(
    agent_data: AgentDetails,
    cat=check_permissions("CONVERSATION", "WRITE"),
) -> Dict:
    # Validazione parametri - tutti devono essere valorizzati
    if not agent_data.agent_name or not agent_data.agent_name.strip():
        return {
            "status": 400,
            "message": "agent_name è obbligatorio e non può essere vuoto",
        }

    if not agent_data.agent_description or not agent_data.agent_description.strip():
        return {
            "status": 400,
            "message": "agent_description è obbligatorio e non può essere vuoto",
        }

    if not agent_data.agent_url or not agent_data.agent_url.strip():
        return {
            "status": 400,
            "message": "agent_url è obbligatorio e non può essere vuoto",
        }

    if not agent_data.agent_key or not agent_data.agent_key.strip():
        return {
            "status": 400,
            "message": "agent_key è obbligatorio e non può essere vuoto",
        }

    if agent_data.agent_ssl is None:
        return {"status": 400, "message": "agent_ssl è obbligatorio"}

    if agent_data.agent_port is None:
        return {"status": 400, "message": "agent_port è obbligatorio"}

    # Percorso del file JSON per l'agente
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    agent_file_path = os.path.join(agents_dir, f"{agent_data.agent_name}.json")

    # Dati dell'agente da salvare
    agent_data_json = {
        "agent_name": agent_data.agent_name,
        "agent_description": agent_data.agent_description,
        "agent_url": agent_data.agent_url,
        "agent_port": agent_data.agent_port,
        "agent_ssl": agent_data.agent_ssl,
        "agent_key": agent_data.agent_key,
    }

    try:
        # Verifica se il file esiste
        if os.path.exists(agent_file_path):
            log.info(f"Aggiornamento agente esistente: {agent_data.agent_name}")
        else:
            log.info(f"Creazione nuovo agente: {agent_data.agent_name}")

        # Assicura che la directory agents esista
        os.makedirs(agents_dir, exist_ok=True)

        # Salva i dati nel file JSON (crea o aggiorna)
        with open(agent_file_path, "w", encoding="utf-8") as f:
            json.dump(agent_data_json, f, indent=2, ensure_ascii=False)

        log.info(
            f"Agente {agent_data.agent_name} salvato con successo in {agent_file_path}"
        )
        return {"status": 200, "message": "agent successfully registered"}

    except Exception as e:
        error_msg = f"Errore durante la registrazione dell'agente {agent_data.agent_name}: {str(e)}"
        log.error(error_msg)
        return {"status": 400, "message": str(e)}


@endpoint.delete(path="/delete-agent/{agent}", prefix="/multicat")
def delete_agent(agent: str, cat=check_permissions("CONVERSATION", "WRITE")) -> Dict:
    """Cancella il file JSON dell'agente specificato dal path param {agent}."""
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    agent_file_path = os.path.join(agents_dir, f"{agent}.json")

    try:
        if not os.path.exists(agent_file_path):
            log.info(f"Tentativo di cancellare agente non esistente: {agent}")
            return {"status": 400, "message": f"Agent '{agent}' non trovato"}

        os.remove(agent_file_path)
        log.info(f"Agente {agent} cancellato: {agent_file_path}")
        return {"status": 200, "message": f"Agent '{agent}' deleted"}

    except Exception as e:
        log.error(f"Errore durante la cancellazione dell'agente {agent}: {str(e)}")
        return {"status": 400, "message": str(e)}


@endpoint.get(path="/list-agents", prefix="/multicat")
def list_agents(cat=check_permissions("CONVERSATION", "READ")) -> Dict:
    """Ritorna la lista degli agenti registrati leggendo i file JSON nella cartella agents."""
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    agents_list: List[Dict[str, Union[str, None]]] = []

    if not os.path.isdir(agents_dir):
        # Nessun agente registrato
        return {"status": 200, "agents": agents_list}

    for fname in os.listdir(agents_dir):
        if not fname.lower().endswith(".json"):
            continue

        file_path = os.path.join(agents_dir, fname)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            agents_list.append(
                {
                    "agent_name": data.get("agent_name"),
                    "agent_description": data.get("agent_description"),
                    "agent_url": data.get("agent_url"),
                    "agent_ssl": data.get("agent_ssl"),
                }
            )
        except Exception as e:
            log.error(f"Impossibile leggere il file agente {file_path}: {str(e)}")
            # skip file corrotti ma continuiamo
            continue

    return {"status": 200, "agents": agents_list}
