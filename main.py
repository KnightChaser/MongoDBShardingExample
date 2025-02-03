import secrets
from pymongo import MongoClient, errors
from tqdm import tqdm

# Connect to the mongos router on the host's port 30000.
try:
    client = MongoClient("mongodb://localhost:30000/", serverSelectionTimeoutMS=5000)
    client.list_database_names()
except errors.ServerSelectionTimeoutError as err:
    print("Connection failed:", err)
    exit(1)

db = client["exampleDB"]
collection = db["files"]

# Option 1: Clear the collection at the start.
# Uncomment the following line if you want to start fresh each time.
# db.drop_collection("files")

# Create required indexes.
collection.create_index("filename")
collection.create_index("sha256")

def generate_document():
    """
    Generates a document with:
      - 'filename': a random 256-character hex string with a .jpg extension.
      - 'sha256': a random 64-character hex string simulating a SHA-256 hash.
    """
    filename = secrets.token_hex(128) + ".jpg"
    sha256_hash = secrets.token_hex(32)
    return {"filename": filename, "sha256": sha256_hash}

# -------------------------------------------------------------------
# 1. Insert documents in batches with progress tracked via tqdm.
total_documents = 10_000
batch_size = 1000
num_batches = total_documents // batch_size

print("Starting insertion of 100K documents...")
for _ in tqdm(range(num_batches), desc="Inserting documents"):
    batch = [generate_document() for _ in range(batch_size)]
    collection.insert_many(batch)
print("Insertion complete!\n")
# -------------------------------------------------------------------

def search_exact(filename):
    """
    Search for a document by its exact filename.
    Uses the 'explain' command (with verbosity set to 'executionStats') to print
    which shard provided the result, then fetches and prints the document.
    """
    print("Exact filename search:")
    print(f"Searching for document with filename:\n  {filename}\n")
    
    explain_command = {
        "explain": {
            "find": "files",
            "filter": {"filename": filename}
        },
        "verbosity": "executionStats"
    }
    explain_plan = db.command(explain_command)
    
    query_planner = explain_plan.get("queryPlanner", {})
    winning_plan = query_planner.get("winningPlan", {})
    if winning_plan.get("stage") == "SINGLE_SHARD":
        shards = winning_plan.get("shards", [])
        if shards:
            for shard in shards:
                shard_name = shard.get("shardName", "unknown")
                print(f"Result came from shard: {shard_name}")
        else:
            print("No shard information found in winningPlan.")
    else:
        print("Query plan is not SINGLE_SHARD; check explain output.")

    doc = collection.find_one({"filename": filename})
    if doc:
        print("\nFound document:")
        print(doc)
    else:
        print("Document not found.")
    return doc

def count_prefixes():
    """
    Count how many documents have a 'filename' that starts with
    'c', 'ca', 'caf', and 'cafe' respectively.
    """
    prefixes = ["c", "ca", "caf", "cafe"]
    print("\nPrefix counts:")
    for prefix in prefixes:
        count = collection.count_documents({"filename": {"$regex": f"^{prefix}"}})
        print(f"Documents with filename starting with '{prefix}': {count}")

# -------------------------------------------------------------------
# Option 2: Pick a random sample document using aggregation.
try:
    sample_doc = collection.aggregate([{"$sample": {"size": 1}}]).next()
except StopIteration:
    sample_doc = None

if sample_doc:
    sample_filename = sample_doc["filename"]
    search_exact(sample_filename)
else:
    print("No sample document found for the exact search.")

# 3. Run the prefix count searches.
count_prefixes()

