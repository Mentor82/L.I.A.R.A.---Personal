import PageLayout from './PageLayout';
import './LegalPages.css';

export function Impressum() {
  return (
    <PageLayout>
      <div className="legal-page-content">
        <h1 className="halo-header">Impressum</h1>
        <div className="halo-divider"></div>
        
        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Angaben gemäß § 5 TMG</h2>
          <div className="halo-mono compact-spacing-sm">
            <p><strong>Betreiber:</strong> [Ihr Name / Firmenname]</p>
            <p><strong>Adresse:</strong> [Straße Hausnummer]</p>
            <p>[PLZ Ort]</p>
            <p>[Land]</p>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Kontakt</h2>
          <div className="halo-mono compact-spacing-sm">
            <p><strong>E-Mail:</strong> [email@example.com]</p>
            <p><strong>Telefon:</strong> [+49 xxx xxxxxxx]</p>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV</h2>
          <div className="halo-mono">
            <p>[Vollständiger Name]</p>
            <p>[Adresse wie oben]</p>
          </div>
        </section>

        <div className="halo-divider"></div>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Haftungsausschluss</h2>
          
          <h3 className="legal-subheading">Haftung für Inhalte</h3>
          <p className="legal-text compact-spacing-sm">
            Die Inhalte unserer Seiten wurden mit größter Sorgfalt erstellt. 
            Für die Richtigkeit, Vollständigkeit und Aktualität der Inhalte 
            können wir jedoch keine Gewähr übernehmen.
          </p>

          <h3 className="legal-subheading">Haftung für Links</h3>
          <p className="legal-text compact-spacing-sm">
            Unser Angebot enthält Links zu externen Webseiten Dritter, auf deren 
            Inhalte wir keinen Einfluss haben. Für die Inhalte der verlinkten 
            Seiten ist stets der jeweilige Anbieter oder Betreiber der Seiten 
            verantwortlich.
          </p>

          <h3 className="legal-subheading">Urheberrecht</h3>
          <p className="legal-text">
            Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen 
            Seiten unterliegen dem deutschen Urheberrecht. Die Vervielfältigung, 
            Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der 
            Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung des 
            jeweiligen Autors bzw. Erstellers.
          </p>
        </section>

        <div className="legal-footer halo-mono">
          <p>Stand: Dezember 2025</p>
          <p className="halo-badge">LEGAL COMPLIANCE</p>
        </div>
      </div>
    </PageLayout>
  );
}

export function Datenschutz() {
  return (
    <PageLayout>
      <div className="legal-page-content">
        <h1 className="halo-header">Datenschutzerklärung</h1>
        <div className="halo-divider"></div>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">1. Datenschutz auf einen Blick</h2>
          
          <h3 className="legal-subheading">Allgemeine Hinweise</h3>
          <p className="legal-text compact-spacing-sm">
            Die folgenden Hinweise geben einen einfachen Überblick darüber, was 
            mit Ihren personenbezogenen Daten passiert, wenn Sie diese Website 
            besuchen. <strong>LIARA wurde mit Privacy by Design entwickelt</strong> 
            und verarbeitet Ihre Daten ausschließlich lokal auf Ihrem Server.
          </p>

          <div className="privacy-highlight halo-badge">
            🔒 Alle Daten bleiben auf Ihrem Server • Keine Cloud • Keine Weitergabe
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">2. Datenerfassung auf dieser Website</h2>
          
          <h3 className="legal-subheading">Wer ist verantwortlich für die Datenerfassung?</h3>
          <p className="legal-text compact-spacing-sm">
            Die Datenverarbeitung erfolgt durch den Websitebetreiber (siehe Impressum). 
            Da LIARA als <strong>self-hosted Lösung</strong> konzipiert ist, haben 
            ausschließlich Sie als Betreiber Zugriff auf die Daten.
          </p>

          <h3 className="legal-subheading">Welche Daten werden erfasst?</h3>
          <div className="halo-mono compact-spacing-sm">
            <ul>
              <li>• Benutzername und E-Mail (bei Registrierung)</li>
              <li>• Chat-Nachrichten (lokal gespeichert)</li>
              <li>• Standortdaten (nur mit expliziter Zustimmung)</li>
              <li>• Web-Suchanfragen (nur mit Zustimmung, automatisch gelöscht)</li>
              <li>• Aufgaben, Notizen, Kalendereinträge (lokal gespeichert)</li>
            </ul>
          </div>

          <h3 className="legal-subheading">Wofür nutzen wir Ihre Daten?</h3>
          <p className="legal-text compact-spacing-sm">
            Alle Daten dienen ausschließlich der Bereitstellung der LIARA-Funktionen:
          </p>
          <div className="halo-mono compact-spacing-sm">
            <ul>
              <li>• Personalisierte Konversationen</li>
              <li>• Aufgabenverwaltung</li>
              <li>• Standortbasierte Informationen (z.B. Wetter)</li>
              <li>• Kontextbasierte Antworten</li>
            </ul>
          </div>

          <h3 className="legal-subheading">Welche Rechte haben Sie?</h3>
          <p className="legal-text compact-spacing-sm">
            Sie haben jederzeit das Recht auf:
          </p>
          <div className="halo-mono">
            <ul>
              <li>• Auskunft über gespeicherte Daten (Datenexport-Funktion)</li>
              <li>• Berichtigung unrichtiger Daten</li>
              <li>• Löschung Ihrer Daten ("Alle Daten löschen" in Datenschutz-Einstellungen)</li>
              <li>• Einschränkung der Datenverarbeitung</li>
              <li>• Widerruf erteilter Einwilligungen</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">3. Automatisches Löschen</h2>
          <p className="legal-text compact-spacing-sm">
            LIARA implementiert <strong>Privacy by Default</strong>:
          </p>
          <div className="halo-mono compact-spacing-sm">
            <ul>
              <li>• Web-Suchanfragen: 7 Tage Aufbewahrung (konfigurierbar)</li>
              <li>• Standortdaten: 30 Tage oder sofortige Löschung bei Widerruf</li>
              <li>• IP-Adressen: Werden NICHT gespeichert</li>
              <li>• Logs: Nur technische Fehler, keine personenbezogenen Daten</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">4. Externe Dienste (Privacy-Focused)</h2>
          
          <h3 className="legal-subheading">Web-Search (nur mit Zustimmung)</h3>
          <p className="legal-text compact-spacing-sm">
            Wenn Sie die Web-Search-Funktion nutzen, werden Anfragen an folgende 
            Dienste gesendet:
          </p>
          <div className="halo-mono compact-spacing-sm">
            <ul>
              <li>• <strong>DuckDuckGo Instant Answer API</strong> (datenschutzfreundlich, keine Tracking)</li>
              <li>• <strong>Wikipedia REST API</strong> (öffentliche Daten, kein Tracking)</li>
              <li>• <strong>Open-Meteo API</strong> (Wetterdaten, kein API-Key, kein Tracking)</li>
            </ul>
          </div>
          <p className="legal-text">
            <strong>Wichtig:</strong> Es werden KEINE IP-Adressen oder Nutzer-IDs 
            an diese Dienste übermittelt. Die Anfragen sind anonym.
          </p>

          <h3 className="legal-subheading">Standorterkennung</h3>
          <p className="legal-text">
            Die Standorterkennung erfolgt über <strong>ip-api.com</strong> 
            (nur Stadt-Ebene, keine IP-Speicherung). Dies erfordert Ihre 
            explizite Zustimmung und kann jederzeit widerrufen werden.
          </p>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">5. KI-Modelle (100% Lokal)</h2>
          <p className="legal-text">
            LIARA nutzt <strong>Ollama</strong> für die KI-Verarbeitung. 
            Alle Modelle laufen <strong>lokal auf Ihrem Server</strong>. 
            Keine Daten werden an OpenAI, Google, Anthropic oder andere 
            Cloud-Anbieter gesendet.
          </p>
        </section>

        <div className="halo-divider"></div>
        <div className="legal-footer halo-mono">
          <p>Stand: Dezember 2025</p>
          <p className="halo-badge">PRIVACY FIRST • NO CLOUD • NO TRACKING</p>
        </div>
      </div>
    </PageLayout>
  );
}

export function AGB() {
  return (
    <PageLayout>
      <div className="legal-page-content">
        <h1 className="halo-header">Allgemeine Geschäftsbedingungen (AGB)</h1>
        <div className="halo-divider"></div>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">§ 1 Geltungsbereich</h2>
          <p className="legal-text compact-spacing-sm">
            Diese Allgemeinen Geschäftsbedingungen gelten für die Nutzung von 
            <strong> LIARA</strong>, einer selbst gehosteten KI-Assistentin.
          </p>
          <p className="legal-text">
            LIARA ist eine <strong>Open-Source Software</strong>, die Sie auf 
            Ihrer eigenen Infrastruktur betreiben. Die Nutzung ist kostenlos.
          </p>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">§ 2 Leistungsumfang</h2>
          <p className="legal-text compact-spacing-sm">
            LIARA bietet folgende Funktionen:
          </p>
          <div className="halo-mono">
            <ul>
              <li>• Konversations-KI (basierend auf lokalen Ollama-Modellen)</li>
              <li>• Aufgaben-, Kalender- und Notizverwaltung</li>
              <li>• Web-Search-Integration (opt-in)</li>
              <li>• 4D-Gedächtnissystem (PostgreSQL, Neo4j, Redis, Embeddings)</li>
              <li>• Privacy-First Design (alle Daten lokal)</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">§ 3 Nutzungsbedingungen</h2>
          <p className="legal-text compact-spacing-sm">
            Die Nutzung von LIARA ist an folgende Bedingungen geknüpft:
          </p>
          <div className="halo-mono compact-spacing-sm">
            <ul>
              <li>• Sie betreiben LIARA auf eigener Infrastruktur</li>
              <li>• Sie sind selbst für Datensicherung verantwortlich</li>
              <li>• Sie nutzen die Software in Übereinstimmung mit geltendem Recht</li>
              <li>• Sie verwenden LIARA nicht für illegale Zwecke</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">§ 4 Haftungsausschluss</h2>
          <p className="legal-text compact-spacing-sm">
            LIARA wird "as is" bereitgestellt. Der Betreiber übernimmt keine 
            Gewährleistung für:
          </p>
          <div className="halo-mono">
            <ul>
              <li>• Fehlerfreien Betrieb</li>
              <li>• Verfügbarkeit der KI-Modelle</li>
              <li>• Richtigkeit der KI-generierten Antworten</li>
              <li>• Datenverlust (Sie sind für Backups verantwortlich)</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">§ 5 Open Source Lizenz</h2>
          <p className="legal-text">
            LIARA ist Open-Source Software. Die genauen Lizenzbedingungen 
            finden Sie in der <code className="halo-mono">LICENSE</code> 
            Datei im Repository.
          </p>
        </section>

        <div className="halo-divider"></div>
        <div className="legal-footer halo-mono">
          <p>Stand: Dezember 2025</p>
          <p className="halo-badge">SELF-HOSTED • OPEN SOURCE • COMMUNITY</p>
        </div>
      </div>
    </PageLayout>
  );
}

export function Cookies() {
  return (
    <PageLayout>
      <div className="legal-page-content">
        <h1 className="halo-header">Cookie-Richtlinie</h1>
        <div className="halo-divider"></div>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Was sind Cookies?</h2>
          <p className="legal-text">
            Cookies sind kleine Textdateien, die auf Ihrem Computer gespeichert 
            werden, wenn Sie eine Website besuchen.
          </p>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Welche Cookies verwendet LIARA?</h2>
          <p className="legal-text compact-spacing-sm">
            LIARA verwendet <strong>ausschließlich essentielle Cookies</strong>, 
            die für den Betrieb notwendig sind:
          </p>
          <div className="halo-mono">
            <ul>
              <li>• <strong>liara_token</strong> - Authentifizierung (Session-Cookie)</li>
              <li>• <strong>liara_guest_mode</strong> - Gast-Modus Status</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Keine Tracking-Cookies</h2>
          <div className="privacy-highlight halo-badge" style={{ marginBottom: '1rem' }}>
            ✅ LIARA verwendet KEINE Tracking-, Marketing- oder Analyse-Cookies
          </div>
          <p className="legal-text compact-spacing-sm">
            Im Gegensatz zu den meisten Websites verwendet LIARA:
          </p>
          <div className="halo-mono">
            <ul>
              <li>• ❌ KEIN Google Analytics</li>
              <li>• ❌ KEINE Facebook Pixel</li>
              <li>• ❌ KEINE Werbe-Tracker</li>
              <li>• ❌ KEINE Third-Party Cookies</li>
            </ul>
          </div>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">LocalStorage & SessionStorage</h2>
          <p className="legal-text compact-spacing-sm">
            Zusätzlich zu Cookies verwendet LIARA HTML5 Web Storage:
          </p>
          <div className="halo-mono compact-spacing-sm">
            <ul>
              <li>• <strong>localStorage:</strong> Speichert Theme-Präferenzen lokal</li>
              <li>• <strong>sessionStorage:</strong> Temporäre Daten während der Sitzung</li>
            </ul>
          </div>
          <p className="legal-text">
            Diese Daten werden <strong>niemals</strong> an Server übertragen 
            und bleiben ausschließlich in Ihrem Browser.
          </p>
        </section>

        <section className="legal-section compact-spacing">
          <h2 className="legal-subtitle">Cookies verwalten</h2>
          <p className="legal-text compact-spacing-sm">
            Sie können Cookies in Ihrem Browser jederzeit löschen oder blockieren:
          </p>
          <div className="halo-mono">
            <ul>
              <li>• <strong>Chrome:</strong> Einstellungen → Datenschutz → Cookies</li>
              <li>• <strong>Firefox:</strong> Einstellungen → Datenschutz → Cookies</li>
              <li>• <strong>Safari:</strong> Einstellungen → Datenschutz</li>
            </ul>
          </div>
          <p className="legal-text">
            <strong>Hinweis:</strong> Wenn Sie alle Cookies blockieren, 
            funktioniert die Anmeldung bei LIARA nicht mehr.
          </p>
        </section>

        <div className="halo-divider"></div>
        <div className="legal-footer halo-mono">
          <p>Stand: Dezember 2025</p>
          <p className="halo-badge">NO TRACKING • ESSENTIAL ONLY • PRIVACY</p>
        </div>
      </div>
    </PageLayout>
  );
}
