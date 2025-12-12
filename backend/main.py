from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from gedcom_parser import parse_gedcom_content
from duplicate_finder import find_duplicates

app = FastAPI()

# Limite de taille de fichier : 100 MB (en octets)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Servir les fichiers statiques du frontend
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
def index():
    # Rediriger vers le fichier HTML statique
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.post("/check-duplicates")
async def check_duplicates(file: UploadFile = File(...)):
    # lire le contenu du .ged uploadé
    raw_bytes = await file.read()

    # Vérifier la taille du fichier
    file_size = len(raw_bytes)
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Le fichier est trop volumineux ({size_mb:.1f} MB). La taille maximale autorisée est de 100 MB."
        )

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # beaucoup de GEDCOM sont en ANSI / ISO-8859-1
        text = raw_bytes.decode("latin-1")

    individuals, families = parse_gedcom_content(text)
    dups = find_duplicates(individuals)

    # On renvoie du JSON. Le front va l'afficher joliment.
    return JSONResponse(dups)

# Pour lancer en local : uvicorn main:app --reload --port 3001
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)