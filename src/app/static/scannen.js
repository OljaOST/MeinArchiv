"use strict";

const formular = document.querySelector("#scan-formular");
const dateiauswahl = document.querySelector("#aufnahme");
const editor = document.querySelector("#scan-editor");
const bild = document.querySelector("#scan-bild");
const abmessungen = document.querySelector("#scan-abmessungen");
const statusText = document.querySelector("#scan-status");
const fehlerText = document.querySelector("#scan-fehler");
const uebernehmen = document.querySelector("#scan-uebernehmen");
const zuschnitt = document.querySelector("#scan-zuschnitt");
const ausschnitt = document.querySelector("#scan-ausschnitt");
const zuschneiden = document.querySelector("#scan-zuschneiden");
const linksDrehen = document.querySelector("#scan-links");
const rechtsDrehen = document.querySelector("#scan-rechts");
const reset = document.querySelector("#scan-reset");
const ausschneiden = document.querySelector("#scan-ausschneiden");
const abbrechen = document.querySelector("#scan-abbrechen");
const seiten = ["links", "rechts", "oben", "unten"];
const regler = Object.fromEntries(
    seiten.map((seite) => [seite, document.querySelector(`#rand-${seite}`)])
);
const MAX_DATEIGROESSE = 10 * 1024 * 1024;
const MAX_BILDSEITE = 2800;

let original = null;
let originalname = "scan";
let ladeNummer = 0;
let beschaeftigt = false;

function zeigeFehler(text) {
    fehlerText.textContent = text;
    fehlerText.hidden = false;
}

function loescheFehler() {
    fehlerText.textContent = "";
    fehlerText.hidden = true;
}

function kopiereBild(quelle) {
    const kopie = document.createElement("canvas");
    kopie.width = quelle.width;
    kopie.height = quelle.height;
    kopie.getContext("2d").drawImage(quelle, 0, 0);
    return kopie;
}

function zeigeBild(quelle) {
    bild.width = quelle.width;
    bild.height = quelle.height;
    bild.getContext("2d").drawImage(quelle, 0, 0);
    abmessungen.textContent = `${bild.width} × ${bild.height} Pixel`;
}

function aktualisiereBedienung() {
    const zuschnittOffen = !zuschnitt.hidden;
    uebernehmen.disabled = beschaeftigt || !original || zuschnittOffen;
    dateiauswahl.disabled = beschaeftigt;
    for (const knopf of [linksDrehen, rechtsDrehen, reset, zuschneiden]) {
        knopf.disabled = beschaeftigt || !original || zuschnittOffen;
    }
    formular.setAttribute("aria-busy", String(beschaeftigt));
}

function aktualisiereAusschnitt() {
    // Mindestens fünf Prozent der Breite und Höhe bleiben erhalten.
    for (const [erste, zweite] of [["links", "rechts"], ["oben", "unten"]]) {
        regler[erste].max = 95 - Number(regler[zweite].value);
        regler[zweite].max = 95 - Number(regler[erste].value);
    }
    for (const seite of seiten) {
        document.querySelector(`#wert-${seite}`).textContent = `${regler[seite].value} %`;
    }
    ausschnitt.style.left = `${regler.links.value}%`;
    ausschnitt.style.right = `${regler.rechts.value}%`;
    ausschnitt.style.top = `${regler.oben.value}%`;
    ausschnitt.style.bottom = `${regler.unten.value}%`;
}

function beendeZuschnitt() {
    zuschnitt.hidden = true;
    ausschnitt.hidden = true;
    zuschneiden.setAttribute("aria-expanded", "false");
    aktualisiereBedienung();
}

function ladeFoto(datei) {
    return new Promise((resolve, reject) => {
        const adresse = URL.createObjectURL(datei);
        const foto = new Image();
        foto.onload = () => {
            URL.revokeObjectURL(adresse);
            resolve(foto);
        };
        foto.onerror = () => {
            URL.revokeObjectURL(adresse);
            reject(new Error("Das Bild konnte nicht geöffnet werden. Bitte wähle ein gültiges JPG- oder PNG-Bild."));
        };
        foto.src = adresse;
    });
}

dateiauswahl.addEventListener("change", async () => {
    const nummer = ++ladeNummer;
    const datei = dateiauswahl.files[0];
    original = null;
    editor.hidden = true;
    loescheFehler();
    beendeZuschnitt();
    statusText.textContent = "";
    if (!datei) return;

    if (!/\.(jpe?g|png)$/i.test(datei.name)) {
        zeigeFehler("Bitte wähle ein JPG- oder PNG-Bild.");
        return;
    }
    if (datei.size > MAX_DATEIGROESSE) {
        zeigeFehler("Das Bild ist grösser als 10 MB. Bitte wähle eine kleinere Datei.");
        return;
    }
    beschaeftigt = true;
    statusText.textContent = "Foto wird vorbereitet …";
    aktualisiereBedienung();
    try {
        const foto = await ladeFoto(datei);
        if (nummer !== ladeNummer) return;
        const faktor = Math.min(1, MAX_BILDSEITE / Math.max(foto.naturalWidth, foto.naturalHeight));
        original = document.createElement("canvas");
        original.width = Math.max(1, Math.round(foto.naturalWidth * faktor));
        original.height = Math.max(1, Math.round(foto.naturalHeight * faktor));
        const kontext = original.getContext("2d");
        // Transparente Stellen werden beim späteren JPEG-Export weiss.
        kontext.fillStyle = "white";
        kontext.fillRect(0, 0, original.width, original.height);
        kontext.drawImage(foto, 0, 0, original.width, original.height);
        originalname = datei.name.replace(/\.[^.]+$/, "") || "scan";
        zeigeBild(original);
        editor.hidden = false;
        statusText.textContent = faktor < 1
            ? "Foto bereit. Für die Bearbeitung auf maximal 2800 Pixel pro Seite verkleinert."
            : "Foto bereit. Du kannst es drehen, zuschneiden oder direkt übernehmen.";
    } catch (fehler) {
        original = null;
        statusText.textContent = "";
        zeigeFehler(fehler.message);
    } finally {
        beschaeftigt = false;
        aktualisiereBedienung();
    }
});

function dreheFoto(richtung) {
    if (!original || beschaeftigt || !zuschnitt.hidden) return;
    const vorher = kopiereBild(bild);
    bild.width = vorher.height;
    bild.height = vorher.width;
    const kontext = bild.getContext("2d");
    kontext.save();
    kontext.translate(bild.width / 2, bild.height / 2);
    kontext.rotate(richtung * Math.PI / 2);
    kontext.drawImage(vorher, -vorher.width / 2, -vorher.height / 2);
    kontext.restore();
    abmessungen.textContent = `${bild.width} × ${bild.height} Pixel`;
    statusText.textContent = "Foto um 90 Grad gedreht.";
}

linksDrehen.addEventListener("click", () => dreheFoto(-1));
rechtsDrehen.addEventListener("click", () => dreheFoto(1));
reset.addEventListener("click", () => {
    if (!original || beschaeftigt) return;
    zeigeBild(original);
    beendeZuschnitt();
    loescheFehler();
    statusText.textContent = "Drehung und Zuschnitt zurückgesetzt.";
});

zuschneiden.addEventListener("click", () => {
    for (const seite of seiten) {
        regler[seite].max = 95;
        regler[seite].value = 0;
    }
    zuschnitt.hidden = false;
    ausschnitt.hidden = false;
    zuschneiden.setAttribute("aria-expanded", "true");
    aktualisiereAusschnitt();
    aktualisiereBedienung();
    regler.links.focus();
});
for (const seite of seiten) {
    regler[seite].addEventListener("input", aktualisiereAusschnitt);
}
abbrechen.addEventListener("click", () => {
    beendeZuschnitt();
    zuschneiden.focus();
});
ausschneiden.addEventListener("click", () => {
    const x = Math.floor(bild.width * Number(regler.links.value) / 100);
    const y = Math.floor(bild.height * Number(regler.oben.value) / 100);
    const rechts = Math.ceil(bild.width * (1 - Number(regler.rechts.value) / 100));
    const unten = Math.ceil(bild.height * (1 - Number(regler.unten.value) / 100));
    const neu = document.createElement("canvas");
    neu.width = Math.max(1, rechts - x);
    neu.height = Math.max(1, unten - y);
    neu.getContext("2d").drawImage(bild, x, y, neu.width, neu.height, 0, 0, neu.width, neu.height);
    zeigeBild(neu);
    beendeZuschnitt();
    statusText.textContent = "Ausschnitt übernommen.";
    zuschneiden.focus();
});

formular.addEventListener("submit", async (ereignis) => {
    ereignis.preventDefault();
    if (!original || beschaeftigt || !zuschnitt.hidden) return;
    beschaeftigt = true;
    loescheFehler();
    statusText.textContent = "Bearbeitetes Foto wird hochgeladen …";
    aktualisiereBedienung();
    try {
        const datei = await new Promise((resolve) => bild.toBlob(resolve, "image/jpeg", 0.92));
        if (!datei || datei.size > MAX_DATEIGROESSE) {
            throw new Error("Das bearbeitete Bild konnte nicht gespeichert werden. Bitte verwende ein kleineres Foto.");
        }
        const daten = new FormData();
        daten.append("dokument", datei, `${originalname}.jpg`);
        const antwort = await fetch(formular.action, {method: "POST", body: daten});
        if (!antwort.ok) {
            const inhalt = await antwort.json().catch(() => null);
            throw new Error(inhalt?.fehler || "Der Upload ist fehlgeschlagen. Bitte versuche es erneut.");
        }
        if (!antwort.redirected) {
            throw new Error("Der Upload konnte nicht bestätigt werden. Prüfe bitte deine offenen Entwürfe, bevor du es erneut versuchst.");
        }
        window.location.assign(antwort.url);
    } catch (fehler) {
        statusText.textContent = "";
        zeigeFehler(fehler instanceof TypeError
            ? "Die Verbindung wurde unterbrochen. Prüfe bitte deine offenen Entwürfe, bevor du es erneut versuchst."
            : fehler.message);
        beschaeftigt = false;
        aktualisiereBedienung();
    }
});

aktualisiereBedienung();
