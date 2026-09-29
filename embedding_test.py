from sentence_transformers import SentenceTransformer


model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


documents = [
    "add two numbers together",
    "multiply two numbers",
    "remove a user from the database",
]


document_embeddings = model.encode(documents)

query = "calculate the product of two values"

query_embedding = model.encode(query)

similarities = model.similarity(
    query_embedding,
    document_embeddings
)


print(similarities)