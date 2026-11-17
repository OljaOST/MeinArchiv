const vorschau = document.querySelector("#pdf-vorschau");
const seitenwahl = vorschau.querySelector(".detail-pdf-seitenwahl");
const zurueck = document.querySelector("#pdf-zurueck");
const weiter = document.querySelector("#pdf-weiter");
const seitenstand = document.querySelector("#pdf-seitenstand");
const canvas = document.querySelector("#pdf-seite");
const status = document.querySelector("#pdf-status");

async function oeffneVorschau() {
    status.textContent = "PDF-Vorschau wird geladen …";
    try {
        const bibliothek = new URL("./vendor/pdfjs/", import.meta.url);
        const { GlobalWorkerOptions, getDocument } = await import(new URL("pdf.min.mjs", bibliothek));
        GlobalWorkerOptions.workerSrc = new URL("pdf.worker.min.mjs", bibliothek).href;
        const pdf = await getDocument({
            url: vorschau.dataset.pdf,
            cMapUrl: new URL("cmaps/", bibliothek).href,
            cMapPacked: true,
            standardFontDataUrl: new URL("standard_fonts/", bibliothek).href,
            wasmUrl: new URL("wasm/", bibliothek).href,
            iccUrl: new URL("iccs/", bibliothek).href,
        }).promise;

        let aktuelleSeite = 1;
        let rendert = false;

        async function zeigeSeite(seitennummer) {
            if (rendert || seitennummer < 1 || seitennummer > pdf.numPages) return;
            rendert = true;
            zurueck.disabled = weiter.disabled = true;
            status.textContent = "";
            seitenwahl.setAttribute("aria-busy", "true");

            try {
                const seite = await pdf.getPage(seitennummer);
                const groesse = seite.getViewport({ scale: 1 });
                const pixelbreite = Math.min(1600, Math.max(1, vorschau.clientWidth - 2) *
                    Math.min(2, window.devicePixelRatio || 1));
                const skalierung = Math.min(pixelbreite / groesse.width, 2200 / groesse.height);
                const ausschnitt = seite.getViewport({ scale: skalierung });

                canvas.hidden = true;
                canvas.width = Math.max(1, Math.ceil(ausschnitt.width));
                canvas.height = Math.max(1, Math.ceil(ausschnitt.height));
                await seite.render({ canvas, viewport: ausschnitt }).promise;

                aktuelleSeite = seitennummer;
                seitenstand.textContent = `Seite ${seitennummer} von ${pdf.numPages}`;
                canvas.setAttribute("aria-label", seitenstand.textContent);
                seitenwahl.hidden = false;
                canvas.hidden = false;
            } catch {
                status.textContent = "Diese PDF-Seite konnte nicht angezeigt werden. Du kannst das Dokument herunterladen.";
                canvas.hidden = true;
            } finally {
                rendert = false;
                seitenwahl.removeAttribute("aria-busy");
                zurueck.disabled = aktuelleSeite === 1;
                weiter.disabled = aktuelleSeite === pdf.numPages;
            }
        }

        zurueck.addEventListener("click", () => zeigeSeite(aktuelleSeite - 1));
        weiter.addEventListener("click", () => zeigeSeite(aktuelleSeite + 1));
        await zeigeSeite(1);
    } catch {
        status.textContent = "Die PDF-Vorschau konnte nicht geladen werden. Du kannst das Dokument herunterladen.";
    }
}

void oeffneVorschau();
