from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

print("SUPABASE_URL =", os.getenv("SUPABASE_URL"))
print("SUPABASE_KEY =", os.getenv("SUPABASE_KEY"))

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)