import { ladeImport } from "./import-datei.js";

const dateiauswahl = document.querySelector("#dateiauswahl");
const dateiFeld = document.querySelector("#dokument");

dateiFeld.disabled = false;
dateiFeld.addEventListener("change", async () => {
    const datei = dateiFeld.files[0];
    if (!datei) return;

    dateiFeld.disabled = true;
    if (!await ladeImport(datei, dateiauswahl, "hochladen")) {
        dateiFeld.value = "";
        dateiFeld.disabled = false;
    }
});
