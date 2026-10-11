/**
 * Scrive la versione dell'app nell'HTML costruito. Va eseguito DOPO `vite build`.
 *
 * Aggiunge `<meta name="app-version" content="...">` in `dist/index.html`.
 * La pagina in esecuzione legge quella meta dal DOM e la confronta con quella
 * servita dal server: se differiscono, c'e' un deploy nuovo e l'app ricarica.
 * Vedi `src/version.ts`.
 *
 * L'impronta dipende dal NOME del bundle, che Vite genera dal contenuto: due
 * build identiche danno la stessa impronta e non fanno ricaricare inutilmente.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const HTML = join(process.cwd(), "dist", "index.html");

const html = readFileSync(HTML, "utf8");
const bundle = /assets\/(index-[A-Za-z0-9_-]+\.js)/.exec(html)?.[1];
if (!bundle) {
  console.error("versione: bundle non trovato in index.html");
  process.exit(1);
}

// Il nome del bundle contiene gia' un'impronta del contenuto: si usa quella.
const impronta = bundle.replace(/^index-/, "").replace(/\.js$/, "");

if (html.includes('name="app-version"')) {
  console.log("versione: la meta esiste gia', niente da fare");
  process.exit(0);
}

writeFileSync(
  HTML,
  html.replace("</head>", `  <meta name="app-version" content="${impronta}" />\n  </head>`),
  "utf8",
);
console.log(`versione: ${impronta} scritta in index.html`);
