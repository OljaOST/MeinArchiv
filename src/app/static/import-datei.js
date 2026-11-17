const entwurf = document.querySelector("#upload-entwurf");
const vorschau = document.querySelector("#upload-vorschau");
const speichern = document.querySelector("#upload-speichern");
const dateiname = document.querySelector("#dateiname");
const endung = document.querySelector("#upload-endung");
const verwerfen = document.querySelector("#upload-verwerfen");
const statusText = document.querySelector("#upload-status");
const fehlerText = document.querySelector("#upload-fehler");

let laedt = false;

export function zeigeImportfehler(meldung) {
    statusText.textContent = "";
    fehlerText.textContent = meldung;
    fehlerText.hidden = false;
}

export function importLaeuft() {
    return laedt;
}

export async function ladeImport(datei, einstieg, quelle) {
    laedt = true;
    einstieg.setAttribute("aria-busy", "true");
    fehlerText.hidden = true;
    statusText.textContent = "Dateinamenvorschlag wird erstellt …";

    try {
        const daten = new FormData();
        daten.append("quelle", quelle);
        daten.append("dokument", datei);

        const antwort = await fetch(einstieg.dataset.vorbereiten, {
            method: "POST",
            body: daten,
        });
        const ergebnis = await antwort.json().catch(() => null);
        if (!antwort.ok || !ergebnis?.speichern) {
            const fehler = antwort.status === 413
                ? "Die Datei ist zu gross. Die Uploadgrenze beträgt 10 MB."
                : "Das Dokument konnte nicht vorbereitet werden. Versuche es erneut.";
            throw new Error(ergebnis?.fehler || fehler);
        }

        speichern.action = ergebnis.speichern;
        speichern.elements.bestaetigung.value = ergebnis.bestaetigung;
        dateiname.value = ergebnis.stamm;
        dateiname.maxLength = 255 - ergebnis.endung.length;
        endung.textContent = ergebnis.endung;
        verwerfen.href = ergebnis.verwerfen;

        const dateiendung = ergebnis.endung.toLowerCase();
        if (dateiendung === ".pdf") {
            const pdf = document.createElement("iframe");
            pdf.title = "PDF-Vorschau";
            pdf.src = ergebnis.vorschau;
            vorschau.append(pdf);
            vorschau.hidden = false;
        } else if ([".jpg", ".jpeg", ".png"].includes(dateiendung)) {
            const bild = document.createElement("img");
            bild.alt = "Vorschau des Dokuments";
            bild.src = ergebnis.vorschau;
            vorschau.append(bild);
            vorschau.hidden = false;
        }

        statusText.textContent = ergebnis.ki_erkannt
            ? ""
            : "Der KI-Namensvorschlag ist nicht verfügbar. Du kannst den bisherigen Namen ändern.";
        einstieg.hidden = true;
        entwurf.hidden = false;
        dateiname.focus();
        return true;
    } catch (fehler) {
        zeigeImportfehler(fehler instanceof TypeError
            ? "Die Verbindung wurde unterbrochen. Versuche es erneut."
            : fehler.message);
        return false;
    } finally {
        laedt = false;
        einstieg.removeAttribute("aria-busy");
    }
}
