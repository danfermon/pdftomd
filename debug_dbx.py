import os
import dropbox
from dotenv import load_dotenv

load_dotenv()
token = os.environ.get('DROPBOX_ACCESS_TOKEN')

if not token:
    print("No token found")
    exit(1)

dbx = dropbox.Dropbox(token)
try:
    account = dbx.users_get_current_account()
    print(f"Name: {account.name.display_name}")
    print(f"Account Type: {account.account_type}")
    
    if hasattr(account, 'root_info') and account.root_info:
        print(f"Root Info Type: {type(account.root_info)}")
        print(f"Root Namespace ID: {account.root_info.root_namespace_id}")
        print(f"Home Namespace ID: {account.root_info.home_namespace_id}")
    else:
        print("No root_info found.")
        
    print("\nAttempting to list namespaces (if supported)...")
    try:
        namespaces = dbx.team_namespaces_list()
        print(f"Found {len(namespaces.namespaces)} team namespaces.")
    except Exception as e:
        print(f"Could not list team namespaces: {e}")
        
except Exception as e:
    print(f"Error: {e}")
