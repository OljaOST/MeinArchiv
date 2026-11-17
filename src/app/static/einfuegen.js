import { importLaeuft, ladeImport, zeigeImportfehler } from "./import-datei.js";

const einfuegebereich = document.querySelector("#einfuegebereich");

document.addEventListener("paste", (ereignis) => {
    if (einfuegebereich.hidden) return;
    ereignis.preventDefault();
    if (importLaeuft()) return;

    const dateien = ereignis.clipboardData?.files;
    if (dateien?.length !== 1) {
        zeigeImportfehler(dateien?.length > 1
            ? "Bitte füge genau ein Dokument auf einmal ein."
            : "Die Zwischenablage enthält kein unterstütztes Dokument.");
        return;
    }

    void ladeImport(dateien[0], einfuegebereich, "einfuegen");
});
