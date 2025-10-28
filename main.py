from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import re
from collections import defaultdict

app = FastAPI()

########################
# 1. GEDCOM PARSER
########################

def parse_gedcom_content(content: str):
    lines = [line.rstrip("\n\r") for line in content.splitlines()]

    individuals = {}
    families = {}

    current_id = None
    current_type = None

    # 1) Première passe : on récupère les individus, familles, noms, liens bruts
    for line in lines:
        parts = line.split(" ", 2)

        if len(parts) == 3 and parts[0] == "0" and parts[1].startswith("@") and parts[2] in ("INDI", "FAM"):
            current_id = parts[1].strip("@")
            current_type = parts[2]

            if current_type == "INDI":
                individuals[current_id] = {
                    "id": current_id,
                    "name_raw": None,
                    "first_name": None,
                    "last_name": None,
                    "birth_date": None,
                    "birth_place": None,
                    "father_id": None,
                    "mother_id": None,
                    "family_as_child": None,
                }
            elif current_type == "FAM":
                families[current_id] = {
                    "id": current_id,
                    "husband_id": None,
                    "wife_id": None,
                    "children_ids": []
                }

            continue

        if current_type == "INDI":
            if line.startswith("1 NAME "):
                name_val = line[len("1 NAME "):]
                individuals[current_id]["name_raw"] = name_val
                m = re.match(r"([^/]+)/([^/]+)/?", name_val)
                if m:
                    individuals[current_id]["first_name"] = m.group(1).strip() or None
                    individuals[current_id]["last_name"] = m.group(2).strip() or None

            elif line.startswith("1 FAMC "):
                famc = line[len("1 FAMC "):].strip()
                famc = famc.strip("@")
                individuals[current_id]["family_as_child"] = famc

        elif current_type == "FAM":
            if line.startswith("1 HUSB "):
                husb = line[len("1 HUSB "):].strip().strip("@")
                families[current_id]["husband_id"] = husb
            elif line.startswith("1 WIFE "):
                wife = line[len("1 WIFE "):].strip().strip("@")
                families[current_id]["wife_id"] = wife
            elif line.startswith("1 CHIL "):
                child = line[len("1 CHIL "):].strip().strip("@")
                families[current_id]["children_ids"].append(child)

    # 2) Deuxième passe : extraire naissance (1 BIRT -> 2 DATE / 2 PLAC)
    current_id = None
    in_birth_block = False
    for line in lines:
        parts = line.split(" ", 2)

        if len(parts) == 3 and parts[0] == "0" and parts[1].startswith("@") and parts[2] == "INDI":
            current_id = parts[1].strip("@")
            in_birth_block = False
            continue

        if current_id is None:
            continue

        if line.startswith("1 BIRT"):
            in_birth_block = True
            continue

        if line.startswith("1 ") and not line.startswith("1 BIRT"):
            in_birth_block = False

        if in_birth_block:
            if line.startswith("2 DATE "):
                individuals[current_id]["birth_date"] = line[len("2 DATE "):].strip() or None
            elif line.startswith("2 PLAC "):
                individuals[current_id]["birth_place"] = line[len("2 PLAC "):].strip() or None

    # 3) Associer père/mère via la famille d'enfant
    for ind_id, ind in individuals.items():
        famc = ind["family_as_child"]
        if famc and famc in families:
            ind["father_id"] = families[famc]["husband_id"]
            ind["mother_id"] = families[famc]["wife_id"]

    return individuals, families


########################
# 2. DUPLICATE FINDER
########################

def find_duplicates(individuals):
    groups = defaultdict(list)

    for ind in individuals.values():
        first = (ind["first_name"] or "").strip().lower()
        last = (ind["last_name"] or "").strip().lower()
        birth = (ind["birth_date"] or "").strip().lower()

        # Ignorer les fiches totalement vides
        if first == "" and last == "" and birth == "":
            continue

        key = (first, last, birth)
        groups[key].append(ind)

    duplicates_report = []

    for key, people in groups.items():
        if len(people) > 1:
            for i in range(len(people)):
                for j in range(i + 1, len(people)):
                    a = people[i]
                    b = people[j]

                    same_parents = (
                        a["father_id"] == b["father_id"]
                        and a["mother_id"] == b["mother_id"]
                        and a["father_id"] is not None
                    )

                    duplicates_report.append({
                        "a_id": a["id"],
                        "b_id": b["id"],
                        "first_name": a["first_name"] or "",
                        "last_name": a["last_name"] or "",
                        "birth_date": a["birth_date"] or "",
                        "birth_place_a": a["birth_place"] or "",
                        "birth_place_b": b["birth_place"] or "",
                        "same_parents": same_parents,
                    })

    return duplicates_report


########################
# 3. FRONTEND HTML
########################
UPLOAD_PAGE = """
<!DOCTYPE html>
<html lang="fr" style="font-family: system-ui, sans-serif; background:#f5f5f5; color:#222;">
<head>
  <meta charset="UTF-8" />
  <title>Détecteur de doublons généalogiques</title>
  
  <style>
    button {
      background: #222;
      color: #fff;
      border: none;
      border-radius: 0.5rem;
      padding: 0.75rem 1rem;
      font-size: 1rem;
      cursor: pointer;
      transition: background 0.2s ease, transform 0.1s ease;
    }
    
    /* effet au survol */
    button:hover {
      background: #444; /* plus clair */
      transform: translateY(-1px);
    }
    
    /* effet clic */
    button:active {
      background: #111;
      transform: translateY(0);
    }
  </style>
  
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
  
</head>
<body style="max-width:600px;margin:2rem auto;background:white;padding:2rem;border-radius:1rem;box-shadow:0 10px 30px rgba(0,0,0,0.07);">
  <h1 style="font-size:1.4rem;line-height:1.2;margin:0 0 1rem;text-align: center;">
    👋 Bonjour Jean-Louis !
  </h1>
  <h1 style="font-size:1.4rem;line-height:1.2;margin:0 0 1rem;text-align: center;">
    Comment allez-vous aujourd'hui ?
  </h1>
  <h2 style="font-size:1.2rem;line-height:1.4;margin:0 0 1rem;font-weight:600;">
    Analyse des doublons dans l'arbre généalogique
  </h2>
  <p style="margin-bottom:1rem;font-size:0.95rem;line-height:1.4;">
    Déposez votre fichier .ged puis cliquez sur "Analyser".
  </p>

  <form id="uploadForm" style="display:flex;flex-direction:column;gap:1rem;">
    <div id="dropzone"
         style="
          border:2px dashed #999;
          border-radius:0.75rem;
          padding:1.5rem;
          text-align:center;
          cursor:pointer;
          background:#fafafa;
          transition:background .15s,border-color .15s;
         "
    >
      <p style="margin:0 0 .5rem;font-size:0.95rem;font-weight:500;color:#111;">
        Déposez votre fichier .ged ici
      </p>
      <p style="margin:0;font-size:0.85rem;color:#555;">
        ou cliquez pour le sélectionner
      </p>
      <p id="fileName"
         style="margin-top:1rem;font-size:0.8rem;color:#888;font-style:italic;">
         Aucun fichier choisi
      </p>
      <!-- input file caché -->
      <input type="file" id="gedFile" accept=".ged" style="display:none;" />
    </div>

    <button type="submit"
      style="background:#222;color:#fff;border:0;border-radius:0.5rem;padding:0.75rem 1rem;font-size:1rem;cursor:pointer;">
      Analyser
    </button>
  </form>
  
    <div id="actions-btn" style="display:none;gap:1rem; margin-top: 1rem;">
      <button id="printBtn" style="flex: 1 0 0; background:#222;color:#fff;border:0;border-radius:0.5rem;padding:0.75rem 1rem;font-size:1rem;cursor:pointer;">🖨️ Imprimer / PDF</button>
      <button id="pdfBtn" style="flex: 1 0 0; background:#222;color:#fff;border:0;border-radius:0.5rem;padding:0.75rem 1rem;font-size:1rem;cursor:pointer;">📄 Télécharger le rapport</button>
    </div>


  <div id="result"
    style="margin-top:2rem;background:#fafafa;border:1px solid #ddd;border-radius:0.5rem;padding:1rem;font-family:monospace;white-space:pre-wrap;font-size:0.9rem;line-height:1.4;">
    En attente d'analyse...
  </div>

<script>

// Récup des éléments du DOM (ils existent maintenant)
const dropzone = document.getElementById("dropzone");
const hiddenInput = document.getElementById("gedFile");
const fileNameLabel = document.getElementById("fileName");

const actionsBtn = document.getElementById("actions-btn");
const pdfBtn = document.getElementById('pdfBtn');
const printBtn = document.getElementById('printBtn');

// Affiche le bouton seulement après une analyse réussie
function showActionButtons() {
  printBtn.style.display = "inline-block";
  pdfBtn.style.display = "inline-block";
}

printBtn.addEventListener('click', () => {
  const printContents = document.getElementById('result').innerHTML;
  const printWindow = window.open('', '_blank', 'width=800,height=600');

  // Contenu HTML de la fenêtre d'impression
  printWindow.document.write(`
    <html>
      <head>
        <title>Rapport généalogique</title>
        <style>
          body {
            font-family: system-ui, sans-serif;
            padding: 2rem;
            background: #fff;
            color: #222;
          }
          h2 {
            margin-bottom: 0.5rem;
          }
          pre {
            background: #fafafa;
            border: 1px solid #ddd;
            border-radius: 0.5rem;
            padding: 1rem;
            font-family: monospace;
            white-space: pre-wrap;
            font-size: 0.9rem;
            line-height: 1.4;
          }
        </style>
      </head>
      <body>
        <h2>Analyse des doublons dans l'arbre généalogique</h2>
        <p style="font-size: 0.9rem; color: #555;">
          Rapport généré le ${new Date().toLocaleString('fr-FR')}
        </p>
        <pre>${printContents}</pre>
      </body>
    </html>
  `);

  printWindow.document.close();

  // Attendre que le contenu soit bien chargé avant d'imprimer
  printWindow.onload = () => {
    printWindow.focus();
    printWindow.print();
  };
});



const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('gedFile');
const resultDiv = document.getElementById('result');

// --- Drag & drop logic ---

// 1. Clic sur la zone -> ouvre le sélecteur de fichier
dropzone.addEventListener("click", () => {
  hiddenInput.click();
});

// 2. Quand on choisit un fichier via le sélecteur classique
hiddenInput.addEventListener("change", () => {
  if (hiddenInput.files && hiddenInput.files[0]) {
    fileNameLabel.textContent = hiddenInput.files[0].name;
  } else {
    fileNameLabel.textContent = "Aucun fichier choisi";
  }
});

// 3. Empêcher le comportement par défaut du navigateur sur drag&drop
["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
  dropzone.addEventListener(eventName, (e) => {
    e.preventDefault();
    e.stopPropagation();
  });
});

// 4. Style visuel quand on survole avec un fichier
["dragenter", "dragover"].forEach(eventName => {
  dropzone.addEventListener(eventName, () => {
    dropzone.style.background = "#f0f9ff";
    dropzone.style.borderColor = "#111";
  });
});
["dragleave", "drop"].forEach(eventName => {
  dropzone.addEventListener(eventName, () => {
    dropzone.style.background = "#fafafa";
    dropzone.style.borderColor = "#999";
  });
});

// 5. Gestion du drop du fichier
dropzone.addEventListener("drop", (e) => {
  const dt = e.dataTransfer;
  const file = dt.files && dt.files[0];
  if (file) {
    if (!file.name.toLowerCase().endsWith(".ged")) {
      fileNameLabel.textContent = "Format non reconnu (attendu .ged)";
      hiddenInput.value = ""; // reset
      return;
    }
    // On injecte le fichier dropé dans l'<input type="file"> caché
    hiddenInput.files = dt.files;
    fileNameLabel.textContent = file.name;
  }
});

pdfBtn.addEventListener('click', () => {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "pt",
    format: "a4"
  });
  
function fixEncoding(str) {
  if (!str) return "";
  try {
    // Convertit les chaînes UTF-8 mal décodées (cas classique avec jsPDF)
    return decodeURIComponent(escape(str))
      .normalize("NFC");
  } catch (e) {
    // Fallback si la chaîne contient déjà du UTF-16 bien formé
    return str.normalize("NFC");
  }
}



  // Récupère le texte affiché à l'écran
  var fullText = fixEncoding(resultDiv.textContent || "Aucun résultat à imprimer.");
    fullText = fullText
    .replace(/🔸/g, "[Doublon probable]")
    .replace(/🔹/g, "[Doublon possible]");

  // Mise en page
  const marginLeft = 40;
  const marginTopInitial = 60;
  const lineHeight = 16; // points entre lignes
  const usableWidth = doc.internal.pageSize.getWidth() - marginLeft * 2;
  const usableHeight = doc.internal.pageSize.getHeight() - marginTopInitial - 40; // 40 bottom margin

  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);

  // On découpe le gros texte en lignes qui tiennent dans la largeur
  const wrappedLines = doc.splitTextToSize(fullText, usableWidth);

  let cursorY = marginTopInitial;
  let firstPage = true;

  function addHeader() {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text("Doublons potentiels trouvés", marginLeft, 40);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(11);
  }

  // En-tête page 1
  addHeader();

  for (let i = 0; i < wrappedLines.length; i++) {
    const line = wrappedLines[i];

    // Si on dépasse la hauteur dispo -> nouvelle page
    if (cursorY > marginTopInitial + usableHeight) {
      doc.addPage();
      cursorY = marginTopInitial;
      addHeader(); // répéter l'en-tête sur les pages suivantes
    }

    doc.text(line, marginLeft, cursorY);
    cursorY += lineHeight;
  }

  const now = new Date();
const formattedDate = now.toLocaleString("fr-FR", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
}).replace(/[/:]/g, "-").replace(",", "");

doc.save(`rapport_genealogique_${formattedDate}.pdf`);
});


// --- Soumission du formulaire / appel API ---

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    resultDiv.textContent = "⚠️ Merci de choisir un fichier .ged d'abord.";
    return;
  }

  resultDiv.textContent = "Analyse en cours...";

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/check-duplicates', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      resultDiv.textContent = "Erreur côté serveur (" + response.status + ").";
      return;
    }

    const data = await response.json();

    if (!Array.isArray(data) || data.length === 0) {
      resultDiv.textContent = "✅ Aucun doublon évident trouvé.";
      return;
    }

    // Construire un rendu lisible
    let out = "🔎 Doublons potentiels trouvés :\\n\\n";
    for (const dup of data) {
      const fn = dup.first_name || "(prénom inconnu)";
      const ln = dup.last_name || "(nom inconnu)";
      const bd = dup.birth_date || "(date inconnue)";

      const relationText = dup.same_parents
        ? "🔸 Doublon probable (mêmes parents)"
        : "🔹 Doublon possible (parents différents ou inconnus)";

      out += `- ${fn} ${ln}, né(e) ${bd}\\n  ${relationText}\\n  (fiches ${dup.a_id} et ${dup.b_id})\\n\\n`;
    }

    resultDiv.textContent = out;
    actionsBtn.style.display = "flex";

  } catch (err) {
    resultDiv.textContent = "Erreur réseau ou JavaScript : " + err;
  }
});
</script>
</body>
</html>
"""

########################
# 4. ROUTES API
########################

@app.get("/", response_class=HTMLResponse)
def index():
    return UPLOAD_PAGE

@app.post("/check-duplicates")
async def check_duplicates(file: UploadFile = File(...)):
    # lire le contenu du .ged uploadé
    raw_bytes = await file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # beaucoup de GEDCOM sont en ANSI / ISO-8859-1
        text = raw_bytes.decode("latin-1")

    individuals, families = parse_gedcom_content(text)
    dups = find_duplicates(individuals)

    # On renvoie du JSON. Le front va l'afficher joliment.
    return JSONResponse(dups)

# Pour lancer en local : uvicorn main:app --reload --port 8000
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
