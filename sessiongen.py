from pyrogram import Client


api_id = int(input("Enter the API ID: "))
api_hash = input("Enter the API hash: ")

client = Client("session", api_id, api_hash)
client.start()
client.send_message("me", f"Your session string is \n\n`{client.export_session_string()}`")

