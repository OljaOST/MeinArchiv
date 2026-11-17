"use strict";

const formular = document.querySelector("#scan-formular");
const kameraStart = document.querySelector("#scan-start");
const kameraOeffnen = document.querySelector("#scan-kamera-oeffnen");
const kamera = document.querySelector("#scan-kamera");
const livebild = document.querySelector("#scan-livebild");
const ausloesen = document.querySelector("#scan-ausloesen");
const kameraAbbrechen = document.querySelector("#scan-kamera-abbrechen");
const editor = document.querySelector("#scan-editor");
const bild = document.querySelector("#scan-bild");
const abmessungen = document.querySelector("#scan-abmessungen");
const statusText = document.querySelector("#scan-status");
const fehlerText = document.querySelector("#scan-fehler");
const speichern = document.querySelector("#scan-speichern");
const verwerfen = document.querySelector("#scan-verwerfen");
const ruecklink = document.querySelector("#scan-zurueck");
const namensfeld = document.querySelector("#scan-namensfeld");
const dateiname = document.querySelector("#scan-dateiname");
const nameStatus = document.querySelector("#scan-name-status");
const erneutVersuchen = document.querySelector("#scan-name-erneut");
const zuschnitt = document.querySelector("#scan-zuschnitt");
const ausschnitt = document.querySelector("#scan-ausschnitt");
const zuschneiden = document.querySelector("#scan-zuschneiden");
const linksDrehen = document.querySelector("#scan-links");
const rechtsDrehen = document.querySelector("#scan-rechts");
const reset = document.querySelector("#scan-reset");
const ausschneiden = document.querySelector("#scan-ausschneiden");
const abbrechen = document.querySelector("#scan-abbrechen");

const MAX_DATEIGROESSE = 10 * 1024 * 1024;
const MAX_BILDSEITE = 2800;

let original = null;
let kameraStream = null;
let kameraAnfrage = 0;
let beschaeftigt = false;
let namensvorschlagLaedt = false;
let entwurf = null;
let rahmen;
let zug = null;

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
    speichern.disabled = beschaeftigt || !entwurf || zuschnittOffen;
    dateiname.disabled = beschaeftigt || !entwurf;
    verwerfen.disabled = beschaeftigt || namensvorschlagLaedt;
    ruecklink.setAttribute("aria-disabled", String(verwerfen.disabled));
    for (const knopf of [linksDrehen, rechtsDrehen, reset, zuschneiden]) {
        knopf.disabled = beschaeftigt || !original || zuschnittOffen;
    }
    formular.setAttribute("aria-busy", String(beschaeftigt));
}

function zeigeAusschnitt() {
    ausschnitt.style.left = `${rahmen.links * 100}%`;
    ausschnitt.style.top = `${rahmen.oben * 100}%`;
    ausschnitt.style.right = `${(1 - rahmen.rechts) * 100}%`;
    ausschnitt.style.bottom = `${(1 - rahmen.unten) * 100}%`;
}

function begrenze(wert, minimum, maximum) {
    return Math.max(minimum, Math.min(maximum, wert));
}

function verschiebeAusschnitt(start, ecke, dx, dy) {
    const groesse = bild.getBoundingClientRect();
    // Die Griffe sollen sich auch auf kleinen Displays getrennt greifen lassen.
    const minBreite = Math.min(start.rechts - start.links, 58 / groesse.width);
    const minHoehe = Math.min(start.unten - start.oben, 58 / groesse.height);
    rahmen = { ...start };
    if (ecke) {
        if (ecke.endsWith("l")) {
            rahmen.links = begrenze(start.links + dx, 0, start.rechts - minBreite);
        } else {
            rahmen.rechts = begrenze(start.rechts + dx, start.links + minBreite, 1);
        }
        if (ecke.startsWith("o")) {
            rahmen.oben = begrenze(start.oben + dy, 0, start.unten - minHoehe);
        } else {
            rahmen.unten = begrenze(start.unten + dy, start.oben + minHoehe, 1);
        }
    } else {
        const x = begrenze(dx, -start.links, 1 - start.rechts);
        const y = begrenze(dy, -start.oben, 1 - start.unten);
        rahmen.links += x;
        rahmen.rechts += x;
        rahmen.oben += y;
        rahmen.unten += y;
    }
    zeigeAusschnitt();
}

ausschnitt.addEventListener("pointerdown", (ereignis) => {
    if (zug || ereignis.button !== 0) return;
    const griff = ereignis.target.closest("[data-ecke]");
    ereignis.preventDefault();
    (griff || ausschnitt).focus({ preventScroll: true });
    zug = {
        id: ereignis.pointerId,
        x: ereignis.clientX,
        y: ereignis.clientY,
        start: { ...rahmen },
        ecke: griff?.dataset.ecke,
    };
    ausschnitt.setPointerCapture(ereignis.pointerId);
});

ausschnitt.addEventListener("pointermove", (ereignis) => {
    if (zug?.id !== ereignis.pointerId) return;
    const groesse = bild.getBoundingClientRect();
    verschiebeAusschnitt(
        zug.start, zug.ecke,
        (ereignis.clientX - zug.x) / groesse.width,
        (ereignis.clientY - zug.y) / groesse.height,
    );
});

ausschnitt.addEventListener("lostpointercapture", () => { zug = null; });

ausschnitt.addEventListener("keydown", (ereignis) => {
    const schritte = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
    const richtung = schritte[ereignis.key];
    if (!richtung || !Array.isArray(richtung)) return;
    ereignis.preventDefault();
    const schritt = ereignis.shiftKey ? 0.05 : 0.01;
    verschiebeAusschnitt(rahmen, ereignis.target.dataset.ecke, richtung[0] * schritt, richtung[1] * schritt);
});

function beendeZuschnitt() {
    zuschnitt.hidden = true;
    ausschnitt.hidden = true;
    zuschneiden.setAttribute("aria-expanded", "false");
    aktualisiereBedienung();
}

function kameraSchliessen() {
    kameraAnfrage++;
    kameraStream?.getTracks().forEach((spur) => spur.stop());
    kameraStream = null;
    livebild.srcObject = null;
    ausloesen.disabled = true;
    kamera.hidden = true;
    kameraStart.hidden = !editor.hidden;
}

async function oeffneKamera() {
    loescheFehler();
    if (!navigator.mediaDevices?.getUserMedia) {
        zeigeFehler("Öffne MeinArchiv über HTTPS oder auf diesem Gerät über localhost, um die Kamera zu nutzen.");
        return;
    }

    const anfrage = ++kameraAnfrage;
    kameraStart.hidden = true;
    kamera.hidden = false;
    kameraAbbrechen.focus();
    statusText.textContent = "Kamera wird geöffnet …";
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: { ideal: "environment" },
                width: { ideal: 1920 },
                height: { ideal: 1920 },
            },
            audio: false,
        });
        if (anfrage !== kameraAnfrage) {
            stream.getTracks().forEach((spur) => spur.stop());
            return;
        }
        kameraStream = stream;
        livebild.srcObject = stream;
        await livebild.play();
        if (anfrage === kameraAnfrage) {
            statusText.textContent = "";
            ausloesen.disabled = false;
            ausloesen.focus();
        }
    } catch (fehler) {
        if (anfrage !== kameraAnfrage) return;
        kameraSchliessen();
        statusText.textContent = "";
        zeigeFehler(fehler.name === "NotAllowedError"
            ? "Erlaube den Kamerazugriff in deinem Browser und versuche es erneut."
            : "Die Kamera ist nicht verfügbar. Prüfe, ob eine Kamera angeschlossen und frei ist.");
        kameraOeffnen.focus();
    }
}

kameraOeffnen.addEventListener("click", oeffneKamera);

kameraAbbrechen.addEventListener("click", () => {
    kameraSchliessen();
    statusText.textContent = "";
    kameraOeffnen.focus();
});

ausloesen.addEventListener("click", () => {
    if (!kameraStream || livebild.readyState < 2 || !livebild.videoWidth || !livebild.videoHeight) {
        zeigeFehler("Das Kamerabild ist noch nicht bereit. Versuche es erneut.");
        return;
    }

    const breite = livebild.videoWidth;
    const hoehe = livebild.videoHeight;
    const faktor = Math.min(1, MAX_BILDSEITE / Math.max(breite, hoehe));
    original = document.createElement("canvas");
    original.width = Math.max(1, Math.round(breite * faktor));
    original.height = Math.max(1, Math.round(hoehe * faktor));
    original.getContext("2d").drawImage(livebild, 0, 0, original.width, original.height);
    zeigeBild(original);
    loescheFehler();
    editor.hidden = false;
    document.querySelector("#scan-startseite").hidden = true;
    ruecklink.hidden = false;
    kameraSchliessen();
    aktualisiereBedienung();
    linksDrehen.focus();
    ladeNamensvorschlag();
});

window.addEventListener("pagehide", kameraSchliessen);

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
    rahmen = { links: 0.08, oben: 0.08, rechts: 0.92, unten: 0.92 };
    zuschnitt.hidden = false;
    ausschnitt.hidden = false;
    zuschneiden.setAttribute("aria-expanded", "true");
    zeigeAusschnitt();
    aktualisiereBedienung();
    ausschnitt.focus({ preventScroll: true });
});
abbrechen.addEventListener("click", () => {
    beendeZuschnitt();
    zuschneiden.focus();
});
ausschneiden.addEventListener("click", () => {
    const x = Math.floor(bild.width * rahmen.links);
    const y = Math.floor(bild.height * rahmen.oben);
    const rechts = Math.min(bild.width, Math.ceil(bild.width * rahmen.rechts));
    const unten = Math.min(bild.height, Math.ceil(bild.height * rahmen.unten));
    const neu = document.createElement("canvas");
    neu.width = Math.max(1, rechts - x);
    neu.height = Math.max(1, unten - y);
    neu.getContext("2d").drawImage(bild, x, y, neu.width, neu.height, 0, 0, neu.width, neu.height);
    zeigeBild(neu);
    beendeZuschnitt();
    statusText.textContent = "Ausschnitt übernommen.";
    zuschneiden.focus();
});

async function pdfDaten(quelle) {
    const pdf = await scanAlsPdf(quelle);
    if (pdf.size + 4096 > MAX_DATEIGROESSE) {
        throw new Error("Das PDF ist zu gross. Versuche es mit einem kleineren Ausschnitt.");
    }
    const daten = new FormData();
    daten.append("dokument", pdf, "scan.pdf");
    return daten;
}

async function ladeNamensvorschlag() {
    namensvorschlagLaedt = true;
    erneutVersuchen.hidden = true;
    loescheFehler();
    nameStatus.textContent = "Dateinamenvorschlag wird erstellt …";
    aktualisiereBedienung();
    try {
        const daten = await pdfDaten(original);
        daten.append("quelle", "scan");
        const antwort = await fetch(formular.action, {method: "POST", body: daten});
        const ergebnis = await antwort.json().catch(() => null);
        if (!antwort.ok || !ergebnis?.speichern) {
            throw new Error(ergebnis?.fehler || "Der Namensvorschlag konnte nicht geladen werden.");
        }
        entwurf = ergebnis;
        dateiname.value = entwurf.stamm;
        namensfeld.hidden = false;
        nameStatus.textContent = entwurf.ki_erkannt
            ? ""
            : "Der KI-Namensvorschlag ist nicht verfügbar. Du kannst den Namen ändern.";
    } catch (fehler) {
        nameStatus.textContent = "";
        erneutVersuchen.hidden = false;
        zeigeFehler(fehler.message);
    } finally {
        namensvorschlagLaedt = false;
        aktualisiereBedienung();
    }
}

erneutVersuchen.addEventListener("click", ladeNamensvorschlag);

async function zurueckZumScannen(ereignis) {
    ereignis.preventDefault();
    if (verwerfen.disabled) return;
    beschaeftigt = true;
    loescheFehler();
    aktualisiereBedienung();
    try {
        if (entwurf) {
            const antwort = await fetch(entwurf.verwerfen, {method: "POST"});
            if (!antwort.redirected && antwort.status !== 404) {
                throw new Error("Der Entwurf konnte nicht verworfen werden.");
            }
        }
        window.location.assign(ruecklink.href);
    } catch (fehler) {
        zeigeFehler(fehler.message);
        beschaeftigt = false;
        aktualisiereBedienung();
    }
}

verwerfen.addEventListener("click", zurueckZumScannen);
ruecklink.addEventListener("click", zurueckZumScannen);

formular.addEventListener("submit", async (ereignis) => {
    ereignis.preventDefault();
    if (speichern.disabled) return;
    beschaeftigt = true;
    loescheFehler();
    statusText.textContent = "Scan wird gespeichert …";
    aktualisiereBedienung();
    try {
        const daten = await pdfDaten(bild);
        daten.append("scan_editor", "ja");
        daten.append("dateiname", dateiname.value);
        daten.append("bestaetigung", entwurf.bestaetigung);
        const antwort = await fetch(entwurf.speichern, {method: "POST", body: daten});
        if (!antwort.redirected) {
            const inhalt = await antwort.json().catch(() => null);
            if (inhalt?.bestaetigung) entwurf.bestaetigung = inhalt.bestaetigung;
            throw new Error(inhalt?.fehler || "Der Scan konnte nicht gespeichert werden.");
        }
        window.location.assign(antwort.url);
    } catch (fehler) {
        statusText.textContent = "";
        zeigeFehler(fehler.message);
        beschaeftigt = false;
        aktualisiereBedienung();
    }
});

aktualisiereBedienung();

// Der Einstieg «Scannen» öffnet direkt die Kameravorschau.
oeffneKamera();
