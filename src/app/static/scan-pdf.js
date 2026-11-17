"use strict";

// Bettet jede zugeschnittene Aufnahme als JPEG in eine eigene PDF-Seite ein.
async function scanAlsPdf(bilder) {
    const teile = [];
    const offset = [0];
    const kodierer = new TextEncoder();
    let position = 0;

    function anfuegen(teil) {
        const daten = typeof teil === "string" ? kodierer.encode(teil) : teil;
        teile.push(daten);
        position += daten instanceof Blob ? daten.size : daten.byteLength;
    }

    function objekt(...inhalt) {
        const nummer = offset.length;
        offset.push(position);
        anfuegen(`${nummer} 0 obj\n`);
        inhalt.forEach(anfuegen);
        anfuegen("\nendobj\n");
    }

    anfuegen("%PDF-1.4\n");
    anfuegen(new Uint8Array([37, 226, 227, 207, 211, 10]));
    objekt("<< /Type /Catalog /Pages 2 0 R >>");
    const seitenreferenzen = bilder.map((_, index) => `${3 + index * 3} 0 R`);
    objekt(`<< /Type /Pages /Kids [${seitenreferenzen.join(" ")}] /Count ${bilder.length} >>`);

    for (const bild of bilder) {
        const jpeg = await new Promise((resolve) => bild.toBlob(resolve, "image/jpeg", 0.92));
        if (!jpeg || jpeg.type !== "image/jpeg") {
            throw new Error("Ein Kamerabild konnte nicht als PDF vorbereitet werden.");
        }

        const querformat = bild.width > bild.height;
        const faktor = Math.min(
            (querformat ? 842 : 595) / bild.width,
            (querformat ? 595 : 842) / bild.height,
        );
        const breite = (bild.width * faktor).toFixed(3);
        const hoehe = (bild.height * faktor).toFixed(3);
        const zeichnen = `q\n${breite} 0 0 ${hoehe} 0 0 cm\n/Scan Do\nQ\n`;

        const bildObjekt = offset.length + 1;
        const inhaltsObjekt = bildObjekt + 1;
        objekt(
            `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${breite} ${hoehe}] ` +
            `/Resources << /XObject << /Scan ${bildObjekt} 0 R >> >> /Contents ${inhaltsObjekt} 0 R >>`,
        );
        objekt(
            `<< /Type /XObject /Subtype /Image /Width ${bild.width} /Height ${bild.height} ` +
            `/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.size} >>\nstream\n`,
            jpeg,
            "\nendstream",
        );
        objekt(`<< /Length ${zeichnen.length} >>\nstream\n${zeichnen}endstream`);
    }

    const startxref = position;
    anfuegen(`xref\n0 ${offset.length}\n0000000000 65535 f \n`);
    for (const wert of offset.slice(1)) {
        anfuegen(`${String(wert).padStart(10, "0")} 00000 n \n`);
    }
    anfuegen(`trailer\n<< /Size ${offset.length} /Root 1 0 R >>\nstartxref\n${startxref}\n%%EOF\n`);
    return new Blob(teile, { type: "application/pdf" });
}
