// Récup des éléments du DOM
const dropzone = document.getElementById("dropzone");
const hiddenInput = document.getElementById("gedFile");
const fileNameLabel = document.getElementById("fileName");
const actionsBtn = document.getElementById("actions-btn");
const pdfBtn = document.getElementById('pdfBtn');
const printBtn = document.getElementById('printBtn');
const form = document.getElementById('uploadForm');
const fileInput = document.getElementById('gedFile');
const resultDiv = document.getElementById('result');

// Limite de taille de fichier : 100 MB (en octets)
const MAX_FILE_SIZE = 100 * 1024 * 1024;

// === DRAG & DROP LOGIC ===

// Fonction pour vérifier la taille du fichier
function validateFileSize(file) {
  if (file.size > MAX_FILE_SIZE) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
    fileNameLabel.textContent = `❌ Fichier trop volumineux (${sizeMB} MB). Maximum : 100 MB`;
    fileNameLabel.style.color = "#dc2626";
    hiddenInput.value = ""; // reset
    resultDiv.textContent = `⚠️ Le fichier est trop volumineux (${sizeMB} MB). La taille maximale autorisée est de 100 MB.`;
    return false;
  }
  fileNameLabel.style.color = "";
  return true;
}

// 1. Clic sur la zone -> ouvre le sélecteur de fichier
dropzone.addEventListener("click", () => {
  hiddenInput.click();
});

// 2. Quand on choisit un fichier via le sélecteur classique
hiddenInput.addEventListener("change", () => {
  if (hiddenInput.files && hiddenInput.files[0]) {
    const file = hiddenInput.files[0];
    if (validateFileSize(file)) {
      fileNameLabel.textContent = file.name;
    }
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
    // Vérifier la taille avant d'accepter le fichier
    if (!validateFileSize(file)) {
      return;
    }
    // On injecte le fichier dropé dans l'<input type="file"> caché
    hiddenInput.files = dt.files;
    fileNameLabel.textContent = file.name;
  }
});

// === PRINT FUNCTIONALITY ===

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

// === PDF FUNCTIONALITY ===

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

pdfBtn.addEventListener('click', () => {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "pt",
    format: "a4"
  });

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

// === FORM SUBMISSION / API CALL ===

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    resultDiv.textContent = "⚠️ Merci de choisir un fichier .ged d'abord.";
    return;
  }

  // Vérification côté client avant l'upload
  if (!validateFileSize(file)) {
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
      // Gestion spécifique de l'erreur 413 (fichier trop volumineux)
      if (response.status === 413) {
        const errorData = await response.json();
        resultDiv.textContent = `⚠️ ${errorData.detail || 'Le fichier est trop volumineux. Maximum : 100 MB'}`;
      } else {
        resultDiv.textContent = "Erreur côté serveur (" + response.status + ").";
      }
      return;
    }

    const data = await response.json();

    if (!Array.isArray(data) || data.length === 0) {
      resultDiv.textContent = "✅ Aucun doublon évident trouvé.";
      return;
    }

    // Construire un rendu lisible
    let out = "🔎 Doublons potentiels trouvés :\n\n";
    for (const dup of data) {
      const fn = dup.first_name || "(prénom inconnu)";
      const ln = dup.last_name || "(nom inconnu)";
      const bd = dup.birth_date || "(date inconnue)";

      const relationText = dup.same_parents
        ? "🔸 Doublon probable (mêmes parents)"
        : "🔹 Doublon possible (parents différents ou inconnus)";

      out += `- ${fn} ${ln}, né(e) ${bd}\n  ${relationText}\n  (fiches ${dup.a_id} et ${dup.b_id})\n\n`;
    }

    resultDiv.textContent = out;
    actionsBtn.style.display = "flex";

  } catch (err) {
    resultDiv.textContent = "Erreur réseau ou JavaScript : " + err;
  }
});