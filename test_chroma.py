from services.vectorstore import VectorStoreService

vs = VectorStoreService()

print("=" * 50)
print("TOTAL DOCUMENTS:", vs.count())
print("=" * 50)

print("\nSearching companies...\n")

companies = vs.search_similar_companies("AI")

print(companies)

print("\nSearching emails...\n")

emails = vs.search_similar_emails("AI Engineer")

print(emails)