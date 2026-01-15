# Docmost Markdown Converter (Docling Edition)

Eine produktionsfähige Anwendung zur Konvertierung von Dokumenten (PDF, DOCX, XLSX) in Docmost-kompatible Markdown-ZIP-Archive. Gesteuert durch **Docling** (Extraktion) und **Ollama** (KI-Veredelung).

## Features

- **Multiformat**: PDF, DOCX, XLSX.
- **Batch Processing**: Verarbeitet mehrere Dateien nacheinander (Client-Side Batching zur Vermeidung von Timeouts).
- **Docmost Ready**: Erstellt automatisch eine Struktur (`Import.md` + Unterseiten), die direkt in Docmost importiert werden kann.
- **KI-Optimierung**: Nutzt Ollama (Llama 3), um das Markdown zu bereinigen und zu strukturieren.
- **Bilder-Support**: Extrahiert Bilder und bindet sie korrekt ein.

## Voraussetzungen

- **Docker** & **Docker Compose** installiert.
- (Optional) Eine GPU für Ollama/Docling wird empfohlen.

## Installation & Start

Da die Images automatisch via GitHub Actions gebaut werden, ist kein lokaler Build notwendig.

1.  Repository klonen oder `docker-compose.yml` herunterladen.
2.  Container herunterladen und starten:

    ```bash
    # Images aktualisieren
    docker-compose pull

    # Starten im Hintergrund
    docker-compose up -d
    ```

3.  Die Anwendung ist erreichbar unter: [http://localhost:3000](http://localhost:3000)

## Konfiguration

Die Konfiguration erfolgt über eine `.env` Datei im gleichen Verzeichnis wie die `docker-compose.yml`.

Beispielinhalt der `.env`:
```env
DOCLING_SERVER_URL=http://host.docker.internal:8080
OLLAMA_SERVER_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gpt-oss:20b
```

*Tipp: Jedes Ollama-Modell funktioniert, aber wir empfehlen **`gpt-oss:20b`** für die besten Ergebnisse bei der deutschen Textveredelung.*

## Nutzung

1.  Öffnen Sie `http://localhost:3000`.
2.  Laden Sie Ihre Dokumente via Drag & Drop hoch.
3.  Klicken Sie auf **"Konvertierung starten"**.
4.  Der Prozess läuft sequentiell ab (um Ressourcen zu schonen).
5.  Am Ende erhalten Sie eine `.zip` Datei.

### Import in Docmost

1.  **Entpacken Sie das ZIP-Archiv NICHT!**
2.  Importieren Sie das ZIP direkt in Docmost.
3.  Es wird eine Seite **"Import"** erstellt, die alle Ihre Dokumente als Unterseiten enthält.
