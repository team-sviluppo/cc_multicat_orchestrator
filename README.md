# ⚡ Multicat Orchestrator

**Multicat Orchestrator** is a plugin part of Multicat, a multiagent system for Cheshire Cat AI. Multicat is composed by 2 plugins:

- **Orchestrator** (this plugin)
- **Agent**: https://github.com/team-sviluppo/cc_multicat_agent

## ✨ Multigent approach

Multicat is **NOT** a multiagent network where each agent interact with other agent, there is an "Orchestrator" that receive the user message and choose the best agent to solve/reply the user request.
**Orchestrator and each agent are indipendent Cheshire Cat instances.**

## 🎯 Multicat use case

A Multicat use case is a chatbot on a website that must respond to completely different topics, such as questions related to the pre-sales phase, support requests, and questions about active contracts/products already purchased by a specific user. In this scenario, Multicat can have a specific agent for each topic, and the Orchestrator will choose the most suitable one based on the user's request.

## ✨ Key Features

- **⭐ Automatic agent registration**: The Agent plugin automatically register new agent on Orchestrator
- **🧠 Use LLM to choose the best agent**: On each messge received the orchestrator use its configured LLM to cohose the best agent to solve/reply user question
- **🔄 Shared data**: Possibility to automatically add "shared data" (for example user information) to message sent to agents
- **⚡ Single QDRANT instance**: All instances (Orchestrator + Agents) can use single QDRANT instance on stack, all data are automatically separated for each agent and orchestrator
- **🌍 Multilingual**: Support fotr English and Italian agents.
- **⚙️ Configurable Agents**: Each agent can be customized with other Cheshire Cat plugins for specific use case customization

## 🚀 Quick Start

### Prerequisites

This plugin requires multiple Cheshire Cat instances with the **Mulricat Agent** plugin installed and configured (see Examlpe Section)

- **🔑 API KEY**: the CCAT_API_KEY env value must be set on Orchestrator instance

### Orchestrator Configuration

The plugin offers several configurable parameters:

- **Language**: Choose the Language for agents (Italian or English)
- **Shared Data**: Data to share on eanche message to the agests (can be overrided on the user message json sent to Orchestartor)
- **Show Agent Why**: Add the agent "Why" to the response send from Orchestrator to User

### Tech Info

The plugin add some custom endpoints:

- **/multicat/register-agent**: Rest endpoint to register new agent (used by Agetn plugin)
- **/multicat/delete-agent/{agent_name}**: Rest endpoint to unregister new agent (used by Agetn plugin)
- **/multicat/list-agents**: get a list of registered agents on Orchestrator

It is possible to override/sedn shared data simply add it to json message sent to the orchestrator:

```
{
"text": "When my account expire?",
"shared_data": {
        "user_id": 10,
        "user_email": "test@test.com"
     },
}
```

The Orchestartor add some useful information on the json response set to the user (on the "WHY" section):

- **selected_agent**: The name of the agent used to generate the response
- **shared_data**: Shared data passed to the agent
- **agent_why**: The WHY generated from the agent (only if enabled in settings)

### Example

This docker compose example create a Mulitcat network with the orchetsrator (on port 80) and one agent specialized on math problems (on port 81):

```
services:
  cheshire_cat_orchestrator:
    image: ghcr.io/cheshire-cat-ai/core:latest
    container_name: cheshire_cat_orchestrator
    environment:
      - TZ=${CCAT_TIMEZONE:-UTC}
      - CCAT_CORE_HOST=localhost
      - CCAT_CORE_PORT=80
      - CCAT_CORE_USE_SECURE_PROTOCOLS=false
      - CCAT_API_KEY=meow
    ports:
      - 80:80
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - TZ=${CCAT_TIMEZONE:-UTC}
    volumes:
      - ./orchestrator_data/static:/app/cat/static
      - ./orchestrator_data/plugins:/app/cat/plugins
      - ./orchestrator_data/data:/app/cat/data
  cheshire-cat-math-agent:
    image: ghcr.io/cheshire-cat-ai/core:latest
    container_name: cheshire_cat_math_agent
    environment:
      - TZ=${CCAT_TIMEZONE:-UTC}
      - CCAT_CORE_HOST=localhost
      - CCAT_CORE_PORT=81
      - CCAT_CORE_USE_SECURE_PROTOCOLS=false
      - CCAT_API_KEY=meow
      - CCAT_API_KEY_WS=meow2
    ports:
      - 81:80
    volumes:
      - ./agents_data/math_agent/static:/app/cat/static
      - ./agents_data/math_agent/plugins:/app/cat/plugins
      - ./agents_data/math_agent/data:/app/cat/data
```

1. Run **_docker compose up -d_** to run the stack
2. Connect to Orchestrator (http://localhost/admin) and instal the Orchestrator Plugin (this repo)
3. Connect to Agent (http://localhost:81/admin) and instal the Agent Plugin (https://github.com/team-sviluppo/cc_multicat_agent)
4. On the Agent Plugin setting insert:

- **Orchestrator Url**: http://host.docker.internal
- **Orchestrator Key**: meow
- **Agent name**: math_agent
- **Agent Description**: This agent is specialized to solve math problems or reply about math questions

5. Configure LLM/Embdeddings settings on Orchestrator and Agent
6. Send a message to the Orchestrator:

```
{
    "text": "There are 49 dogs signed up for a dog show. There are 36 more small dogs than large dogs. How many small dogs have signed up to compete?"
}
```

7. Check the response JSON from the Orchestrator to check if additional data are present

```
"selected_agent": "math_agent",
"shared_data": "",
"agent_why": {
    "input": "There are 49 dogs signed up for a dog show. There are 36 more small dogs than large dogs. How many small dogs have signed up to compete?",
    "intermediate_steps": [],
    "memory": {
        "episodic": [
             {
             ...
```
