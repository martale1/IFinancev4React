/**
 * Scrive la versione dell'app nei file che la pagina puo' controllare.
 *
 * Va eseguito PRIMA di `tsc` e `vite build`, perche' `src/versioneCostruita.ts`
 * finisce dentro il bundle. L'impronta e' il commit git: cambia a ogni deploy.
 *
 * PERCHE' NON BASTA LA META NELL'HTML: il meccanismo precedente leggeva la
 * versione dalla `<meta name="app-version">` dell'HTML in esecuzione e la
 * confrontava con quella servita dal server. Se il browser teneva in cache un
 * HTML vecchio, la pagina confrontava una versione vecchia con una vecchia e non
 * ricaricava mai: il controllo si fidava proprio del file sospetto. Misurato: la
 * pagina serviva il bundle precedente e la versione coincideva, quindi nessun
 * ricaricamento.
 *
 * ADESSO la versione sta in DUE posti che non dipendono dall'HTML:
 *   - dentro il bundle (`versioneCostruita.ts`), cioe' il codice che gira davvero;
 *   - in `dist/version.json`, servito dal backend senza cache.
 * Se il bundle in esecuzione e' vecchio, il confronto lo scopre e ricarica.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join } from "node:path";

const radice = process.cwd();
const fileBundle = join(radice, "src", "versioneCostruita.ts");
const fileJson = join(radice, "dist", "version.json");

/** Il commit corrente, o un valore di ripiego se git non e' disponibile. */
function impronta() {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], { cwd: radice, encoding: "utf8" }).trim();
  } catch {
    return "senza-git";
  }
}

const versione = impronta();

// 1) Dentro il bundle: e' la versione del CODICE IN ESECUZIONE. Si scrive sempre,
//    perche' serve PRIMA della compilazione: e' questa costante che finisce nel
//    bundle e permette di scoprire una copia vecchia.
writeFileSync(
  fileBundle,
  `// File generato da scripts/versione.mjs: non modificare a mano.\n` +
    `// Contiene il commit di questa build, per accorgersi di una copia vecchia.\n` +
    `// Il tipo e' annotato come string: senza, TypeScript restringerebbe il tipo al\n` +
    `// valore letterale e rifiuterebbe il confronto con la versione del server.\n` +
    `export const VERSIONE_COSTRUITA: string = "${versione}";\n`,
  "utf8",
);

// 2) Fuori dal bundle: la versione che il server serve ADESSO. Si scrive solo
//    dopo `vite build`, perche' `dist/` deve esistere.
if (existsSync(join(radice, "dist"))) {
  writeFileSync(fileJson, JSON.stringify({ version: versione }) + "\n", "utf8");

  const html = join(radice, "dist", "index.html");
  if (existsSync(html)) {
    const testo = readFileSync(html, "utf8");
    if (testo.includes('name="app-version"')) {
      writeFileSync(html, testo.replace(/(name="app-version"\s+content=")[^"]*(")/, `$1${versione}$2`), "utf8");
    } else {
      writeFileSync(html, testo.replace("</head>", `  <meta name="app-version" content="${versione}" />\n  </head>`), "utf8");
    }
  }
  console.log(`versione: ${versione} (bundle + version.json + meta)`);
} else {
  console.log(`versione: ${versione} (solo bundle: la cartella dist non esiste ancora)`);
}
