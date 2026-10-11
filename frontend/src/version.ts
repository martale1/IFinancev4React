/**
 * Versione dell'app, per accorgersi quando il browser mostra una copia vecchia.
 *
 * PERCHE' SERVE: quando il deploy cambia, la `index.html` puo' restare in cache
 * nel browser. Il suo contenuto cambia solo in una riga (il nome del bundle),
 * quindi il browser puo' decidere di non ricontrollarla e continuare a caricare
 * il bundle vecchio. Risultato: l'utente non vede le novita' anche se sono
 * online, e ricaricare la pagina non basta.
 *
 * COME FUNZIONA: uno script dopo la build scrive
 * `<meta name="app-version" content="...">` nell'HTML. La pagina in esecuzione
 * legge quel valore dal DOM e lo confronta con quello che il server serve ORA
 * (`cache: "no-store"`). Se sono diversi, c'e' un deploy nuovo e si ricarica.
 *
 * Perche' dal DOM e non da una costante nel bundle: il bundle e' minificato, e
 * sostituire una costante al suo interno sarebbe fragile. La meta e' parte
 * dell'HTML, che e' esattamente il file di cui stiamo verificando la freschezza.
 */

const META = 'meta[name="app-version"]';

/** La versione della pagina attualmente in esecuzione, o null se assente. */
function versioneInEsecuzione(): string | null {
  return document.querySelector(META)?.getAttribute("content") ?? null;
}

/** La versione servita dal server in questo momento. */
async function versioneDalServer(): Promise<string | null> {
  try {
    // `no-store` per non farsi ingannare proprio dalla cache che stiamo cercando
    // di scoprire. Il parametro evita anche le cache intermedie.
    const risposta = await fetch(`/?_v=${Date.now()}`, { cache: "no-store" });
    if (!risposta.ok) return null;
    const html = await risposta.text();
    const trovata = /<meta\s+name="app-version"\s+content="([^"]+)"/i.exec(html);
    return trovata ? trovata[1] : null;
  } catch {
    // Rete assente o server irraggiungibile: non e' il caso di ricaricare.
    return null;
  }
}

/**
 * True se il server serve una versione diversa da quella in esecuzione.
 * Se una delle due manca (sviluppo, build senza lo script) non fa nulla.
 */
export async function c_eUnaVersioneNuova(): Promise<boolean> {
  const esecuzione = versioneInEsecuzione();
  if (!esecuzione) return false;
  const server = await versioneDalServer();
  return Boolean(server) && server !== esecuzione;
}
