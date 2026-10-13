/**
 * Versione dell'app, per accorgersi quando il browser mostra una copia vecchia.
 *
 * PERCHE' SERVE: quando il deploy cambia, la `index.html` puo' restare in cache
 * nel browser. Il suo contenuto cambia solo in una riga (il nome del bundle),
 * quindi il browser puo' decidere di non ricontrollarla e continuare a caricare
 * il bundle vecchio. Risultato: l'utente non vede le novita' anche se sono
 * online, e ricaricare la pagina non basta.
 *
 * COME FUNZIONA ADESSO — e perche' non come prima. Il meccanismo precedente
 * leggeva la versione dalla `<meta name="app-version">` dell'HTML in esecuzione e
 * la confrontava con quella servita dal server. Sembrava ragionevole, ma si
 * fidava proprio del file sospetto: se il browser teneva un HTML vecchio, la
 * pagina confrontava una versione vecchia con una vecchia e **non ricaricava
 * mai**. Difetto misurato: il bundle in esecuzione era quello precedente e le due
 * versioni coincidevano, quindi il controllo taceva.
 *
 * ADESSO il confronto e' fra due cose che NON dipendono dall'HTML:
 *   - `VERSIONE_COSTRUITA`, costante scritta dentro il bundle dalla build: dice
 *     qual e' il codice che sta girando davvero;
 *   - `dist/version.json`, servito dal backend con `no-store`: dice cosa c'e'
 *     online adesso.
 * Se il bundle e' vecchio, il confronto lo scopre. La meta nell'HTML resta come
 * ripiego per i server che non servono ancora il file JSON.
 */

import { VERSIONE_COSTRUITA } from "./versioneCostruita";

const META = 'meta[name="app-version"]';

/** La versione dall'HTML in esecuzione: ripiego, puo' essere una copia vecchia. */
function versioneDallHtml(): string | null {
  return document.querySelector(META)?.getAttribute("content") ?? null;
}

/** La versione servita dal server adesso, letta dal file JSON dedicato. */
async function versioneDaJson(): Promise<string | null> {
  try {
    const risposta = await fetch(`/version.json?_v=${Date.now()}`, { cache: "no-store" });
    if (!risposta.ok) return null;
    const dati = (await risposta.json()) as { version?: unknown };
    return typeof dati.version === "string" ? dati.version : null;
  } catch {
    return null;
  }
}

/** Ripiego: la versione dalla meta dell'HTML appena scaricato, senza cache. */
async function versioneDallHtmlFresco(): Promise<string | null> {
  try {
    const risposta = await fetch(`/?_v=${Date.now()}`, { cache: "no-store" });
    if (!risposta.ok) return null;
    const html = await risposta.text();
    const trovata = /<meta\s+name="app-version"\s+content="([^"]+)"/i.exec(html);
    if (trovata) return trovata[1];
    // Build vecchie, senza meta: si riconosce il bundle dall'HTML fresco.
    const bundle = /assets\/(index-[A-Za-z0-9_-]+)\.js/.exec(html);
    return bundle ? bundle[1].replace(/^index-/, "") : null;
  } catch {
    return null;
  }
}

/**
 * True se il server serve una versione diversa da quella del bundle in esecuzione.
 *
 * Se la versione costruita e' il ripiego (build fatta senza lo script) non si fa
 * nulla: meglio nessun ricaricamento che un ciclo di ricariche.
 */
export async function c_eUnaVersioneNuova(): Promise<boolean> {
  if (!VERSIONE_COSTRUITA || VERSIONE_COSTRUITA === "senza-versione") return false;

  const server = (await versioneDaJson()) ?? (await versioneDallHtmlFresco());
  if (!server) return false;

  if (server === VERSIONE_COSTRUITA) return false;

  // Diagnostica: se la pagina in esecuzione ha una meta DIVERSA da quella
  // costruita, il browser sta davvero mostrando un HTML piu' vecchio del codice
  // che esegue. Utile per capire da dove arriva una copia stantia.
  const daHtml = versioneDallHtml();
  if (daHtml && daHtml !== VERSIONE_COSTRUITA) {
    console.info(
      `[versione] pagina in esecuzione ${VERSIONE_COSTRUITA}, HTML ${daHtml}, server ${server}: ricarico.`,
    );
  }
  return true;
}
