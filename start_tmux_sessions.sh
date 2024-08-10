#!/bin/bash

# Define the session names
CHAINLIT_SESSION="chainlit"
MEMGPT_SESSION="memgpt"
REMINDER_SERVICE_SESSION="reminder-service"
VAPI_SERVICE_SESSION="vapi-service"
GMAIL_SERVICE_SESSION="gmail-service"

# Function to create a new tmux session if it doesn't already exist
create_tmux_session() {
    SESSION_NAME=$1
    COMMAND=$2
    if ! tmux has-session -t $SESSION_NAME 2>/dev/null; then
        tmux new-session -d -s $SESSION_NAME "source /home/plato/dev/ella-ai/ella/bin/activate && source /home/plato/dev/ella-ai/load_env.sh && log_and_export_env && $COMMAND; bash"
        echo "Started new tmux session: $SESSION_NAME"
    else
        echo "Tmux session $SESSION_NAME already exists."
    fi
}

# Create tmux sessions for ChainLit, MemGPT, Reminder-Service, VAPI-Service, and Gmail-Service
create_tmux_session $CHAINLIT_SESSION "cd /home/plato/dev/ella-ai && chainlit run main.py --port 9000"
create_tmux_session $MEMGPT_SESSION "cd /home/plato/dev/ella-ai/memgpt && memgpt server --port 8080"
create_tmux_session $REMINDER_SERVICE_SESSION "cd /home/plato/dev/ella-ai && python reminder_service.py"
create_tmux_session $VAPI_SERVICE_SESSION "cd /home/plato/dev/ella-ai && python vapi_service.py"
create_tmux_session $GMAIL_SERVICE_SESSION "cd /home/plato/dev/ella-ai && python gmail_service.py"

# List active tmux sessions
tmux ls