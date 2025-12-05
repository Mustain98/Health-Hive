from fastapi import FastAPI

app=FastAPI()

@app.get("/")
def root():
    return({"message : Health Hive is running"})