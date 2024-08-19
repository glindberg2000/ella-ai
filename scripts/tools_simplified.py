import requests
from dotenv import load_dotenv
import os
from rich.console import Console
from rich.table import Table
import sqlite3
from pathlib import Path

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

# Constants for base URL and tokens
admin_token = os.getenv("MEMGPT_SERVER_PASS")
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8080")

# SQLite database connection
db_dir = os.getenv("DB_PATH")
if not db_dir:
    console.print("[bold red]Error: DB_PATH environment variable is not set.[/bold red]")
    exit(1)
db_dir = Path(db_dir)
db_file = db_dir / "database.db"

if not db_file.is_file():
    console.print(f"[bold red]Error: Database file not found at {db_file}.[/bold red]")
    exit(1)

conn = sqlite3.connect(db_file)
cursor = conn.cursor()

if not admin_token:
    console.print("[bold red]Error: Admin token is not set in the environment variables.[/bold red]")
    exit(1)

# Function to fetch all users from the API, handling pagination if necessary
def fetch_all_users_from_api():
    url = f"{base_url}/admin/users"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {admin_token}"
    }
    all_users = []
    cursor = None

    while True:
        params = {"limit": 50}
        if cursor:
            params["cursor"] = cursor
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            result = response.json()
            all_users.extend(result.get("user_list", []))
            cursor = result.get("cursor", None)
            
            if not cursor:  # No more pages to fetch
                break
        else:
            console.print(f"[bold red]Failed to fetch users with status code: {response.status_code}[/bold red]")
            break

    console.print(f"[bold green]Total API users returned: {len(all_users)}[/bold green]")
    return all_users

# Function to fetch tools for a specific user from the API
def fetch_tools_for_user(api_key):
    url = f"{base_url}/admin/tools"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            tools = response.json().get("tools", [])
            return [tool.get("name") for tool in tools]
        elif response.status_code == 401:
            console.print(f"[bold red]Unauthorized access. Check the API key: {api_key}[/bold red]")
            return []
        else:
            console.print(f"[bold red]Failed to fetch tools. Status code: {response.status_code}[/bold red]")
            return []
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red]Failed to fetch tools. Error: {e}[/bold red]")
        return []

# Function to fetch the API key for a user from SQLite
def fetch_api_key_for_user(user_id):
    cursor.execute("SELECT memgpt_user_api_key FROM users WHERE memgpt_user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Main function to list users and their tools
def list_users_and_tools():
    users = fetch_all_users_from_api()

    if not users:
        console.print("[bold red]No users found.[/bold red]")
        return

    table = Table(title="MemGPT API User List", title_style="bold magenta")
    table.add_column("Index", justify="center", style="bold cyan")
    table.add_column("User ID", style="bold yellow")
    table.add_column("Tools", style="bold blue")

    for i, user in enumerate(users):
        user_id = user.get("user_id", "Unknown ID")
        api_key = fetch_api_key_for_user(user_id)  # Fetch the API key from SQLite
        if api_key:
            tools = fetch_tools_for_user(api_key)
            tools_list = ", ".join(tools) if tools else "No tools found"
            table.add_row(str(i + 1), user_id, tools_list)
        else:
            console.print(f"[bold red]API key not found for user_id: {user_id}. Skipping...[/bold red]")

    console.print(table)

if __name__ == "__main__":
    list_users_and_tools()
    conn.close()