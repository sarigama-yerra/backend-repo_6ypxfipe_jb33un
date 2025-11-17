import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Literal
from database import db, create_document, get_documents
from schemas import MapSelection
from bson import ObjectId
import csv
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    return response

# ---------- Map selection endpoints ----------
class SelectionCreate(BaseModel):
    name: str
    level: Literal["state", "county"]
    items: List[str]
    notes: str | None = None

@app.post("/api/selections")
def create_selection(payload: SelectionCreate):
    try:
        sel = MapSelection(**payload.model_dump())
        inserted_id = create_document("mapselection", sel)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/selections")
def list_selections():
    try:
        docs = get_documents("mapselection")
        # convert ObjectId and datetime to strings
        def normalize(doc):
            doc["id"] = str(doc.pop("_id", ""))
            for k, v in list(doc.items()):
                if hasattr(v, "isoformat"):
                    doc[k] = v.isoformat()
            return doc
        return [normalize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/selections/{selection_id}")
def get_selection(selection_id: str):
    try:
        docs = list(db["mapselection"].find({"_id": ObjectId(selection_id)}))
        if not docs:
            raise HTTPException(status_code=404, detail="Selection not found")
        d = docs[0]
        d["id"] = str(d.pop("_id", ""))
        for k, v in list(d.items()):
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/selections/{selection_id}/export.csv")
def export_selection_csv(selection_id: str):
    try:
        docs = list(db["mapselection"].find({"_id": ObjectId(selection_id)}))
        if not docs:
            raise HTTPException(status_code=404, detail="Selection not found")
        d = docs[0]
        # prepare CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["name", "level", "item"])
        for item in d.get("items", []):
            writer.writerow([d.get("name", ""), d.get("level", ""), item])
        csv_data = output.getvalue()
        return PlainTextResponse(content=csv_data, media_type="text/csv")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
