from granite_client import GraniteClient

client = GraniteClient()

response = client.generate("Say hello in one sentence.")

print(response)