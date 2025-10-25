from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Server is running!"}

@app.get("/hello/{name}")
def greet(name: str):
    return {"greeting": f"Hey {name}, welcome to your bot server!"}