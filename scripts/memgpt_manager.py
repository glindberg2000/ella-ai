import os
import sys
import requests
from pathlib import Path
import sqlite3
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from memgpt.functions.schema_generator import generate_schema as memgpt_generate_schema
import ast
from pathlib import Path
import importlib.util
import inspect
import json

import logging
import requests
from memgpt.models.pydantic_models import ToolModel

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Load environment variables
load_dotenv()

# Setup
console = Console()
base_url = os.getenv("MEMGPT_API_URL", "http://localhost:8283")
admin_token = os.getenv("MEMGPT_SERVER_PASS")
db_dir = os.getenv("DB_PATH")
tools_dir = os.getenv("MEMGPT_TOOLS_PATH")

# Ensure that DB_PATH is set
if not db_dir:
    console.print("[bold red]Error: DB_PATH environment variable is not set.[/bold red]")
    sys.exit(1)

# Define the full path to the database file
db_file = Path(db_dir) / "database.db"

# Check if the database file exists
if not db_file.is_file():
    console.print(f"[bold red]Error: Database file not found at {db_file}.[/bold red]")
    sys.exit(1)

# Connect to the SQLite database
conn = sqlite3.connect(db_file)
cursor = conn.cursor()


# Ensure that TOOLS PATH is set
if not tools_dir:
    console.print("[bold red]Error: MEMGPT_TOOLS_PATH environment variable is not set.[/bold red]")
    sys.exit(1)

# Define the full path to the custom tools file
custom_tools_path = Path(tools_dir) / "custom_tools.py"

# Check if the custom tools file exists
if not custom_tools_path.is_file():
    console.print(f"[bold red]Error: custom_tools.py file not found at {custom_tools_path}.[/bold red]")
    sys.exit(1)
else:
    console.print(f"[bold green]Custom tools file found at {custom_tools_path}.[/bold green]")


def get_tool_id(api_key, tool_name):
    url = f"{base_url}/api/tools/name/{tool_name}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    try:
        logger.debug(f"Sending GET request to: {url}")
        response = requests.get(url, headers=headers)
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        logger.debug(f"Response content: {response.text[:1000]}...")  # Log first 1000 chars of response

        response.raise_for_status()

        if response.headers.get('Content-Type', '').startswith('application/json'):
            data = response.json()
            logger.debug(f"Parsed JSON data: {data}")
            if isinstance(data, str):
                return data  # It's already the ID
            elif isinstance(data, dict) and 'id' in data:
                return data['id']  # It's a Tool object, return the ID
            else:
                logger.error(f"Unexpected JSON structure: {data}")
                return None
        else:
            logger.warning("Response is not JSON. Attempting to extract ID from content.")
            # Implement fallback logic here if needed
            return None

    except requests.RequestException as e:
        logger.exception(f"Error fetching tool ID: {str(e)}")
        return None

def update_tool(tool_id, api_key, updated_tool_data):
    if not tool_id or not isinstance(tool_id, str) or len(tool_id) > 100:  # Basic validation
        console.print("[bold red]Invalid tool ID. Cannot proceed with update.[/bold red]")
        return None

    url = f"{base_url}/api/tools/{tool_id}"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    
    try:
        console.print(f"[bold blue]Sending POST request to: {url}[/bold blue]")
        console.print(f"[bold blue]Headers: {json.dumps(headers, indent=2)}[/bold blue]")
        console.print(f"[bold blue]Payload: {json.dumps(updated_tool_data, indent=2)}[/bold blue]")
        
        response = requests.post(url, json=updated_tool_data, headers=headers)
        console.print(f"[bold blue]Response status code: {response.status_code}[/bold blue]")
        console.print(f"[bold blue]Response headers: {json.dumps(dict(response.headers), indent=2)}[/bold blue]")
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        console.print(f"[bold red]Error updating tool: {str(e)}[/bold red]")
        if e.response is not None:
            console.print(f"[bold red]Response status code: {e.response.status_code}[/bold red]")
            console.print(f"[bold red]Response content: {e.response.text}[/bold red]")
        return None
                
def update_user_tool(api_key, tools):
    if not tools:
        console.print("[bold yellow]No tools available to update.[/bold yellow]")
        return

    row = input("Enter the row number of the tool to update: ")
    try:
        row = int(row) - 1
        if 0 <= row < len(tools):
            tool = tools[row]
            tool_id = tool.get("id")
            console.print(f"\n[bold cyan]Current tool details:[/bold cyan]")
            for key, value in tool.items():
                console.print(f"{key}: {value}")
            
            console.print("\n[bold cyan]Enter new details (press Enter to keep current value):[/bold cyan]")
            name = input(f"Name [{tool.get('name')}]: ") or tool.get('name')
            description = input(f"Description [{tool.get('description', '')}]: ") or tool.get('description', '')
            source_type = input(f"Source Type [{tool.get('source_type', '')}]: ") or tool.get('source_type', '')
            source_code = input(f"Source Code [{tool.get('source_code', '')}]: ") or tool.get('source_code', '')
            module = input(f"Module [{tool.get('module', '')}]: ") or tool.get('module', '')
            tags = input(f"Tags (comma-separated) [{', '.join(tool.get('tags', []))}]: ") or ', '.join(tool.get('tags', []))

            updated_data = {
                "name": name,
                "description": description,
                "source_type": source_type,
                "source_code": source_code,
                "module": module,
                "tags": tags.split(', ') if tags else []
            }

            result = update_tool(tool_id, api_key, updated_data)
            if result:
                console.print(f"[bold green]Tool '{name}' updated successfully![/bold green]")
            else:
                console.print(f"[bold red]Failed to update tool '{name}'.[/bold red]")
        else:
            console.print("[bold red]Invalid row number.[/bold red]")
    except ValueError:
        console.print("[bold red]Invalid input. Please enter a number.[/bold red]")

def view_user_details(user_id, api_key, email):
    console.print("\n[bold magenta]User Details:[/bold magenta]")
    console.print(f"User ID: {user_id}")
    console.print(f"API Key: {api_key}")
    console.print(f"Email: {email}")
    
    tools = fetch_tools_for_user(api_key)
    if tools:
        console.print("\n[bold magenta]User's Tools:[/bold magenta]")
        display_tools(tools, title="User's Tools")
    else:
        console.print("[bold yellow]No tools found for this user.[/bold yellow]")
    return tools

# def delete_user_tool(api_key, tools):
#     if not tools:
#         console.print("[bold yellow]No tools available to delete.[/bold yellow]")
#         return

#     row = input("Enter the row number of the tool to delete: ")
#     try:
#         row = int(row) - 1
#         if 0 <= row < len(tools):
#             tool = tools[row]
#             tool_name = tool.get("name")
#             result = delete_tool(tool_name, api_key)
#             if result:
#                 console.print(f"[bold green]Tool '{tool_name}' deleted successfully![/bold green]")
#             else:
#                 console.print(f"[bold red]Failed to delete tool '{tool_name}'.[/bold red]")
#         else:
#             console.print("[bold red]Invalid row number.[/bold red]")
#     except ValueError:
#         console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
def delete_user_tool(api_key, tools):
    if not tools:
        console.print("[bold yellow]No tools available to delete.[/bold yellow]")
        return

    console.print("[bold cyan]Delete by row number or tool name?[/bold cyan]")
    console.print("1. Delete by row number")
    console.print("2. Delete by tool name")
    choice = input("Enter your choice (1 or 2): ")

    if choice == "1":
        row = input("Enter the row number of the tool to delete: ")
        try:
            row = int(row) - 1
            if 0 <= row < len(tools):
                tool = tools[row]
                tool_name = tool.get("name")
                result = delete_tool(tool_name, api_key)
                if result:
                    console.print(f"[bold green]Tool '{tool_name}' deleted successfully![/bold green]")
                else:
                    console.print(f"[bold red]Failed to delete tool '{tool_name}'.[/bold red]")
            else:
                console.print("[bold red]Invalid row number.[/bold red]")
        except ValueError:
            console.print("[bold red]Invalid input. Please enter a number.[/bold red]")
    elif choice == "2":
        tool_name = input("Enter the name of the tool to delete: ")
        result = delete_tool(tool_name, api_key)
        if result:
            console.print(f"[bold green]Tool '{tool_name}' deleted successfully![/bold green]")
        else:
            console.print(f"[bold red]Failed to delete tool '{tool_name}'.[/bold red]")
    else:
        console.print("[bold red]Invalid choice. Returning to menu.[/bold red]")

def delete_tool_by_name(api_key):
    tool_name = input("Enter the name of the tool to delete: ")
    result = delete_tool(tool_name, api_key)
    if result:
        console.print(f"[bold green]Tool '{tool_name}' deleted successfully![/bold green]")
    else:
        console.print(f"[bold red]Failed to delete tool '{tool_name}'. It may not exist or you may not have permission to delete it.[/bold red]")

# Add this to your main menu or user interaction menu
def delete_tool_menu(api_key):
    console.print("\n[bold magenta]Delete Tool Menu[/bold magenta]")
    console.print("1. Delete tool from list")
    console.print("2. Delete tool by name (use for missing tools)")
    console.print("3. Return to previous menu")

    choice = input("Enter your choice: ")

    if choice == "1":
        tools = fetch_tools_for_user(api_key)
        delete_user_tool(api_key, tools)
    elif choice == "2":
        delete_tool_by_name(api_key)
    elif choice == "3":
        return
    else:
        console.print("[bold red]Invalid choice. Returning to menu.[/bold red]")
        
def delete_tool(tool_name, api_key):
    url = f"{base_url}/api/tools/{tool_name}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        console.print(f"[bold red]Failed to delete tool '{tool_name}': {str(e)}[/bold red]")
        return False


def get_user_tool_details(api_key, tools):
    if not tools:
        console.print("[bold yellow]No tools available to view details.[/bold yellow]")
        return

    row = input("Enter the row number of the tool to view details: ")
    try:
        row = int(row) - 1
        if 0 <= row < len(tools):
            tool = tools[row]
            tool_name = tool.get("name")
            details = get_tool_details(tool_name, api_key)
            if details:
                console.print(f"[bold green]Tool Details:[/bold green]")
                for key, value in details.items():
                    console.print(f"{key}: {value}")
            else:
                console.print(f"[bold red]Failed to get details for tool '{tool_name}'.[/bold red]")
        else:
            console.print("[bold red]Invalid row number.[/bold red]")
    except ValueError:
        console.print("[bold red]Invalid input. Please enter a number.[/bold red]")

def make_request(endpoint, method="GET", data=None, params=None, api_key=None):
    url = f"{base_url}/{endpoint}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key or admin_token}"
    }
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            headers["content-type"] = "application/json"
            response = requests.post(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, params=params)
        
        response.raise_for_status()
        return response.json() if response.text else None
    except requests.RequestException as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        return None

def fetch_all_users_from_api():
    all_users = []
    cursor = None
    while True:
        params = {"limit": 50, "cursor": cursor} if cursor else {"limit": 50}
        result = make_request("admin/users", params=params)
        if not result:
            break
        all_users.extend(result.get("user_list", []))
        cursor = result.get("cursor")
        if not cursor:
            break
    return all_users

def fetch_tools_for_user(api_key):
    url = f"{base_url}/api/tools"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tools = response.json().get("tools", [])
        return tools
    except requests.RequestException as e:
        console.print(f"[bold red]Error fetching tools: {str(e)}[/bold red]")
        return []

def create_tool(tool_data, api_key):
    url = f"{base_url}/api/tools"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.post(url, json=tool_data, headers=headers)
        response.raise_for_status()
        result = response.json()
        console.print(f"[bold green]Tool created successfully. ID: {result.get('id', 'Unknown')}[/bold green]")
        return result
    except requests.RequestException as e:
        console.print(f"[bold red]Failed to create tool: {str(e)}[/bold red]")
        return None

    
def get_tool_details(tool_name, api_key):
    return make_request(f"api/tools/{tool_name}", api_key=api_key)

def fetch_user_info(memgpt_user_id):
    cursor.execute("SELECT memgpt_user_api_key, email FROM users WHERE memgpt_user_id = ?", (memgpt_user_id,))
    return cursor.fetchone()

def display_users(users):
    table = Table(title="MemGPT API User List", title_style="bold magenta")
    table.add_column("Index", justify="center", style="bold cyan")
    table.add_column("User ID", style="bold yellow")
    table.add_column("API Key", style="bold white")
    table.add_column("Email", style="bold green")
    
    for i, user in enumerate(users, start=1):
        user_id = user.get("user_id", "Unknown ID")
        user_info = fetch_user_info(user_id)
        email = user_info[1] if user_info else "N/A"
        api_key = user_info[0] if user_info else "N/A"
        table.add_row(str(i), user_id, api_key, email)
    
    console.print(table)
    return users

def create_new_tool(api_key):
    console.print("[bold cyan]Create a new tool:[/bold cyan]")
    name = input("Enter tool name: ")
    tags = input("Enter tags (comma-separated): ").split(',')
    source_type = input("Enter source type: ")
    source_code = input("Enter source code: ")
    module = input("Enter module: ")
    
    tool_data = {
        "name": name,
        "tags": tags,
        "source_type": source_type,
        "source_code": source_code,
        "module": module
    }
    
    result = create_tool(tool_data, api_key)
    if result:
        console.print("[bold green]Tool created successfully![/bold green]")
    else:
        console.print("[bold red]Failed to create tool.[/bold red]")

def cleanup_accounts():
    api_users = fetch_all_users_from_api()
    cursor.execute("SELECT memgpt_user_id FROM users")
    sql_users = cursor.fetchall()

    api_user_ids = {user.get("user_id") for user in api_users}
    sql_user_ids = {user[0] for user in sql_users}

    only_in_api = api_user_ids - sql_user_ids
    only_in_sql = sql_user_ids - api_user_ids

    # Exempt the special server account
    special_account = "00000000-0000-0000-0000-000000000000"
    only_in_api.discard(special_account)
    only_in_sql.discard(special_account)

    console.print("\n[bold yellow]Accounts to be deleted from the API (not found in SQL DB):[/bold yellow]")
    for user_id in only_in_api:
        console.print(user_id)

    console.print("\n[bold yellow]Accounts to be deleted from the SQL DB (not found in API):[/bold yellow]")
    for user_id in only_in_sql:
        console.print(user_id)

    confirm = input("Do you want to proceed with the cleanup? (yes/no): ").lower()
    if confirm == "yes":
        for user_id in only_in_api:
            delete_user(user_id)
            console.print(f"[bold green]Deleted API user with user_id: {user_id}[/bold green]")

        for user_id in only_in_sql:
            cursor.execute("DELETE FROM users WHERE memgpt_user_id = ?", (user_id,))
            conn.commit()
            console.print(f"[bold green]Deleted SQL user with user_id: {user_id}[/bold green]")
    else:
        console.print("[bold red]Cleanup operation canceled.[/bold red]")

def get_custom_tools_functions(custom_tools_path):
    """
    Imports the custom_tools.py file, extracts function objects listed in the CUSTOM_TOOLS array,
    and returns them.
    """
    spec = importlib.util.spec_from_file_location("custom_tools", custom_tools_path)
    custom_tools_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(custom_tools_module)
    
    custom_tools_list = getattr(custom_tools_module, 'CUSTOM_TOOLS', [])
    
    if not custom_tools_list:
        console.print("[bold yellow]Warning: CUSTOM_TOOLS list is empty in custom_tools.py[/bold yellow]")
    
    return custom_tools_list

def extract_version_from_docstring(docstring):
    if docstring:
        for line in docstring.split('\n'):
            if line.strip().startswith("Version:"):
                return line.split(":", 1)[1].strip()
    return "Unknown"

def generate_schema(function):
    schema = memgpt_generate_schema(function)
    version = extract_version_from_docstring(function.__doc__)
    schema["version"] = version
    return schema

def display_tools(tools, title="Tools List"):
    table = Table(title=title, title_style="bold magenta")
    table.add_column("Index", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("ID", style="green")
    table.add_column("Version", style="blue")
    
    if isinstance(tools, str):
        try:
            tools = json.loads(tools)
        except json.JSONDecodeError:
            console.print(f"[bold red]Error: Received unexpected string instead of tool list: {tools}[/bold red]")
            return

    if not isinstance(tools, list):
        console.print(f"[bold red]Error: Expected list of tools, got {type(tools)}[/bold red]")
        return

    for index, tool in enumerate(tools, start=1):
        if not isinstance(tool, dict):
            console.print(f"[bold red]Error: Expected dict for tool, got {type(tool)}[/bold red]")
            continue

        name = tool.get("name", "N/A")
        tool_id = tool.get("id", "N/A")
        
        # Try to extract version from source_code if available
        version = "Unknown"
        source_code = tool.get("source_code")
        if source_code:
            version = extract_version_from_docstring(source_code)
        
        table.add_row(str(index), name, tool_id, version)
    
    console.print(table)

def display_custom_functions(functions):
    table = Table(title="Available Custom Functions", title_style="bold magenta")
    table.add_column("Index", style="cyan")
    table.add_column("Function Name", style="yellow")
    table.add_column("Version", style="green")
    table.add_column("Description", style="blue")
    
    for index, func in enumerate(functions, start=1):
        docstring = func.__doc__
        version = extract_version_from_docstring(docstring)
        description = docstring.split('\n')[1].strip() if docstring else "No description available"
        table.add_row(str(index), func.__name__, version, description)
    
    console.print(table)

def update_tool_from_function(api_key, function):
    function_name = function.__name__
    
    console.print(f"[bold blue]Checking for existing tool: {function_name}[/bold blue]")
    existing_tool = get_tool_by_name(api_key, function_name)
    
    if not existing_tool:
        console.print(f"[bold yellow]No existing tool found with name '{function_name}'.[/bold yellow]")
        create_new = input("Would you like to create a new tool with this function? (yes/no): ").lower()
        if create_new == 'yes':
            create_new_tool_from_function(api_key, function)
        return

    console.print(f"[bold green]Existing tool found: {function_name}[/bold green]")

    # Generate schema using the correct function
    schema = generate_schema(function)
    
    # Prepare the new tool data
    new_tool_data = {
        "name": schema["name"],
        "description": schema["description"],
        "source_code": inspect.getsource(function),
        "json_schema": schema,
        "source_type": "python",
        "module": "custom_module",
        "tags": ["updated", "custom"]
    }

    console.print("\n[bold magenta]Update Options:[/bold magenta]")
    console.print("1. Attempt to update existing tool (may not work due to server issues)")
    console.print("2. Delete existing tool and create a new one")
    console.print("3. Cancel update")

    choice = input("Choose an option: ")

    if choice == "1":
        # Existing update method (currently not working)
        console.print("[bold yellow]This option is currently not functioning due to server issues.[/bold yellow]")
    elif choice == "2":
        # Delete and create method
        if delete_tool(function_name, api_key):
            new_tool = create_tool(new_tool_data, api_key)
            if new_tool:
                console.print(f"[bold green]Tool '{schema['name']}' recreated successfully![/bold green]")
                console.print("New tool details:")
                for key, value in new_tool.items():
                    console.print(f"{key}: {value}")
            else:
                console.print(f"[bold red]Failed to recreate tool '{schema['name']}'.[/bold red]")
        else:
            console.print(f"[bold red]Failed to delete existing tool '{schema['name']}'. Update aborted.[/bold red]")
    else:
        console.print("[bold yellow]Update cancelled.[/bold yellow]")

def get_tool_by_name(api_key, tool_name):
    url = f"{base_url}/api/tools"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tools = response.json().get("tools", [])
        return next((tool for tool in tools if tool["name"] == tool_name), None)
    except requests.RequestException as e:
        console.print(f"[bold red]Error fetching tools: {str(e)}[/bold red]")
        return None

def create_new_tool_from_function(api_key, function):
    schema = generate_schema(function)
    tool_data = {
        "name": schema["name"],
        "description": schema["description"],
        "source_code": inspect.getsource(function),
        "json_schema": schema,
        "source_type": "python",
        "module": "custom_module",
        "tags": ["custom"]
    }
    
    result = create_tool(tool_data, api_key)
    if result:
        console.print(f"[bold green]New tool '{schema['name']}' created successfully![/bold green]")
    else:
        console.print(f"[bold red]Failed to create new tool '{schema['name']}'.[/bold red]")
        
def interact_with_user_row(users):
    index = input("Enter the number of the user to interact with: ")
    try:
        index = int(index) - 1
        if 0 <= index < len(users):
            user = users[index]
            user_id = user.get("user_id")
            user_info = fetch_user_info(user_id)
            api_key = user_info[0] if user_info else None
            email = user_info[1] if user_info else "N/A"
            
            console.print(f"\n[bold blue]Selected User: {user_id} (Email: {email})[/bold blue]")
            tools = view_user_details(user_id, api_key, email)
            
            custom_functions = get_custom_tools_functions(custom_tools_path)
            
            while True:
                console.print("\n[bold magenta]User Action Menu[/bold magenta]")
                console.print("1. List available custom functions")
                console.print("2. Update existing tool with custom function")
                console.print("3. Create new tool from custom function")
                console.print("4. View user's tools")
                console.print("5. Delete user's tool")
                console.print("6. Get tool details")
                console.print("7. Return to main menu")

                choice = input("Choose an option: ")

                if choice == "1":
                    display_custom_functions(custom_functions)
                elif choice == "2":
                    display_custom_functions(custom_functions)
                    func_index = int(input("Enter the index of the function to use: ")) - 1
                    if 0 <= func_index < len(custom_functions):
                        update_tool_from_function(api_key, custom_functions[func_index])
                    else:
                        console.print("[bold red]Invalid function index.[/bold red]")

                elif choice == "3":
                    display_custom_functions(custom_functions)
                    func_index = int(input("Enter the index of the function to use: ")) - 1
                    if 0 <= func_index < len(custom_functions):
                        create_new_tool_from_function(api_key, custom_functions[func_index])
                    else:
                        console.print("[bold red]Invalid function index.[/bold red]")
                elif choice == "4":
                    tools = view_user_details(user_id, api_key, email)
                elif choice == "5":
                    delete_user_tool(api_key, tools)
                elif choice == "6":
                    get_user_tool_details(api_key, tools)
                elif choice == "7":
                    break
                else:
                    console.print("[bold red]Invalid option. Please try again.[/bold red]")
        else:
            console.print("[bold red]Invalid index. Returning to main menu.[/bold red]")
    except ValueError:
        console.print("[bold red]Invalid input. Returning to main menu.[/bold red]")

def main_menu():
    while True:
        console.print("\n[bold magenta]MemGPT User and Tool Management CLI[/bold magenta]")
        console.print("1. List All Users")
        console.print("2. Interact with a User")
        console.print("3. Delete User")
        console.print("4. Run Cleanup Utility")
        console.print("0. Exit")

        choice = input("\nEnter your choice: ")

        if choice == "1":
            users = fetch_all_users_from_api()
            display_users(users)
        elif choice == "2":
            users = fetch_all_users_from_api()
            displayed_users = display_users(users)
            interact_with_user_row(displayed_users)
        elif choice == "3":
            user_id = input("Enter the user ID to delete: ")
            result = delete_user(user_id)
            if result:
                console.print(f"[bold green]User {user_id} deleted successfully![/bold green]")
            else:
                console.print(f"[bold red]Failed to delete user {user_id}.[/bold red]")
        elif choice == "4":
            cleanup_accounts()
        elif choice == "0":
            sys.exit(0)
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")

if __name__ == "__main__":
    if not admin_token or not db_dir:
        console.print("[bold red]Admin token or DB directory path is not set in the environment variables.[/bold red]")
        sys.exit(1)
    main_menu()
    conn.close()