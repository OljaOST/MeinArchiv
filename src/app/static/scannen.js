const dateiauswahl = document.querySelector("#aufnahme");
const bildvorschau = document.querySelector("#bildvorschau");
const vorschaubild = document.querySelector("#vorschaubild");

let vorschauAdresse = null;

function entferneVorschau() {
    bildvorschau.hidden = true;
    vorschaubild.removeAttribute("src");

    if (vorschauAdresse !== null) {
        URL.revokeObjectURL(vorschauAdresse);
        vorschauAdresse = null;
    }
}

dateiauswahl.addEventListener("change", () => {
    entferneVorschau();

    const datei = dateiauswahl.files[0];

    if (!datei) {
        return;
    }

    vorschauAdresse = URL.createObjectURL(datei);
    vorschaubild.src = vorschauAdresse;
    bildvorschau.hidden = false;
});

vorschaubild.addEventListener("error", entferneVorschau);

window.addEventListener("pagehide", entferneVorschau);