from services.vectorstore import VectorStoreService

vs = VectorStoreService()

context = vs.get_relevant_context(
    company_name="Enord",
    skills=["Python", "Machine Learning"]
)

print("=" * 60)
print(context)
print("=" * 60)