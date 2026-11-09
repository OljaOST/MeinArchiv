"use strict";

const formular = document.querySelector("#einfuegen-formular");
const einfuegebereich = document.querySelector("#einfuegebereich");
const lesen = document.querySelector("#zwischenablage-lesen");
const auswahl = document.querySelector("#ersatz-datei");
const dokumentBereich = document.querySelector("#eingefuegtes-dokument");
const nameText = document.querySelector("#eingefuegter-name");
const groesseText = document.querySelector("#eingefuegte-groesse");
const bild = document.querySelector("#eingefuegtes-bild");
const vorschauHinweis = document.querySelector("#dokument-vorschau-hinweis");
const entfernen = document.querySelector("#eingefuegtes-entfernen");
const statusText = document.querySelector("#einfuegen-status");
const fehlerText = document.querySelector("#einfuegen-fehler");
const uebernehmen = document.querySelector("#dokument-uebernehmen");
const MAX_DATEIGROESSE = 10 * 1024 * 1024;
const mimeEndungen = new Map([
    ["application/pdf", ".pdf"],
    ["image/png", ".png"],
    ["image/jpeg", ".jpg"],
    ["application/msword", ".doc"],
    ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"],
]);

let aktuelleDatei = null;
let bildAdresse = null;
let beschaeftigt = false;

function zeigeFehler(text) {
    fehlerText.textContent = text;
    fehlerText.hidden = false;
}

function loescheFehler() {
    fehlerText.textContent = "";
    fehlerText.hidden = true;
}

function aktualisiereBedienung() {
    uebernehmen.disabled = beschaeftigt || !aktuelleDatei;
    lesen.disabled = beschaeftigt || !navigator.clipboard?.read;
    auswahl.disabled = beschaeftigt;
    entfernen.disabled = beschaeftigt;
    formular.setAttribute("aria-busy", String(beschaeftigt));
}

function verwerfeAuswahl() {
    aktuelleDatei = null;
    dokumentBereich.hidden = true;
    bild.hidden = true;
    bild.removeAttribute("src");
    if (bildAdresse !== null) {
        URL.revokeObjectURL(bildAdresse);
        bildAdresse = null;
    }
    aktualisiereBedienung();
}

function uebernehmeDatei(datei) {
    verwerfeAuswahl();
    loescheFehler();
    statusText.textContent = "";
    if (!/\.(pdf|jpe?g|png|docx?)$/i.test(datei.name)) {
        zeigeFehler("Bitte füge ein PDF-, JPG-, PNG- oder Word-Dokument ein. Reiner Text wird nicht als Dokument übernommen.");
        return;
    }
    if (datei.name.length > 255) {
        zeigeFehler("Der Dateiname ist zu lang. Bitte benenne die Datei vor dem Einfügen um.");
        return;
    }
    if (!datei.size) {
        zeigeFehler("Die Datei ist leer. Bitte wähle ein anderes Dokument.");
        return;
    }
    if (datei.size > MAX_DATEIGROESSE) {
        zeigeFehler("Die Datei ist grösser als 10 MB. Bitte wähle eine kleinere Datei.");
        return;
    }
    aktuelleDatei = datei;
    nameText.textContent = datei.name;
    groesseText.textContent = datei.size < 1024 * 1024
        ? `${Math.ceil(datei.size / 1024)} KB`
        : `${(datei.size / (1024 * 1024)).toFixed(1)} MB`;
    dokumentBereich.hidden = false;
    vorschauHinweis.hidden = /\.(jpe?g|png)$/i.test(datei.name);
    if (vorschauHinweis.hidden) {
        bildAdresse = URL.createObjectURL(datei);
        bild.src = bildAdresse;
        bild.hidden = false;
    }
    statusText.textContent = "Dokument bereit. Es wurde noch nicht hochgeladen.";
    aktualisiereBedienung();
}

bild.addEventListener("error", () => {
    verwerfeAuswahl();
    statusText.textContent = "";
    zeigeFehler("Das Bild konnte nicht geöffnet werden. Bitte wähle ein gültiges JPG- oder PNG-Bild.");
});

document.addEventListener("paste", (ereignis) => {
    if (beschaeftigt) return;
    ereignis.preventDefault();
    const dateien = Array.from(ereignis.clipboardData?.files || []);
    auswahl.value = "";
    if (dateien.length !== 1) {
        verwerfeAuswahl();
        statusText.textContent = "";
        zeigeFehler(dateien.length > 1
            ? "Bitte füge genau ein Dokument auf einmal ein."
            : "Die Zwischenablage enthält kein verfügbares Dokument. Reiner Text wird nicht übernommen. Kopiere ein Bild oder wähle die Datei unten aus.");
        return;
    }
    uebernehmeDatei(dateien[0]);
});

lesen.addEventListener("click", async () => {
    if (beschaeftigt || !navigator.clipboard?.read) return;
    beschaeftigt = true;
    verwerfeAuswahl();
    auswahl.value = "";
    loescheFehler();
    statusText.textContent = "Zwischenablage wird gelesen …";
    aktualisiereBedienung();
    try {
        const eintraege = await navigator.clipboard.read();
        const dokumente = eintraege.map((eintrag) => ({
            eintrag,
            typ: Array.from(mimeEndungen.keys()).find((typ) => eintrag.types.includes(typ)),
        })).filter((dokument) => dokument.typ);
        if (dokumente.length !== 1) {
            throw new Error(dokumente.length > 1
                ? "Bitte kopiere genau ein Dokument auf einmal."
                : "Kein unterstütztes Dokument verfügbar. Kopiere ein Bild oder verwende die Dateiauswahl unten.");
        }
        const {eintrag, typ} = dokumente[0];
        const inhalt = await eintrag.getType(typ);
        uebernehmeDatei(new File([inhalt], `eingefuegt${mimeEndungen.get(typ)}`, {type: typ}));
    } catch (fehler) {
        statusText.textContent = "";
        zeigeFehler(fehler.name === "NotAllowedError" || fehler.name === "SecurityError"
            ? "Der Browser hat den Zugriff auf die Zwischenablage nicht erlaubt. Versuche ⌘ + V beziehungsweise Strg + V oder verwende die Dateiauswahl."
            : fehler.message || "Die Zwischenablage konnte nicht gelesen werden. Verwende bitte die Dateiauswahl.");
    } finally {
        beschaeftigt = false;
        aktualisiereBedienung();
    }
});

auswahl.addEventListener("change", () => {
    if (auswahl.files[0]) uebernehmeDatei(auswahl.files[0]);
});
entfernen.addEventListener("click", () => {
    verwerfeAuswahl();
    auswahl.value = "";
    loescheFehler();
    statusText.textContent = "Auswahl entfernt.";
    einfuegebereich.focus();
});

formular.addEventListener("submit", async (ereignis) => {
    ereignis.preventDefault();
    if (!aktuelleDatei || beschaeftigt) return;
    beschaeftigt = true;
    loescheFehler();
    statusText.textContent = "Dokument wird hochgeladen …";
    aktualisiereBedienung();
    try {
        const daten = new FormData();
        daten.append("dokument", aktuelleDatei, aktuelleDatei.name);
        const antwort = await fetch(formular.action, {method: "POST", body: daten});
        if (!antwort.ok) {
            const inhalt = await antwort.json().catch(() => null);
            throw new Error(inhalt?.fehler || "Der Upload ist fehlgeschlagen. Bitte versuche es erneut.");
        }
        if (!antwort.redirected) {
            throw new Error("Der Upload konnte nicht bestätigt werden. Prüfe bitte deine offenen Entwürfe vor einem erneuten Versuch.");
        }
        window.location.assign(antwort.url);
    } catch (fehler) {
        statusText.textContent = "";
        zeigeFehler(fehler instanceof TypeError
            ? "Die Verbindung wurde unterbrochen. Prüfe bitte deine offenen Entwürfe vor einem erneuten Versuch."
            : fehler.message);
        beschaeftigt = false;
        aktualisiereBedienung();
    }
});

if (!navigator.clipboard?.read) {
    statusText.textContent = "Verwende zum Einfügen ⌘ + V beziehungsweise Strg + V oder die Dateiauswahl.";
}
aktualisiereBedienung();
