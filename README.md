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

Die Konfiguration erfolgt über Umgebungsvariablen in der `docker-compose.yml`:

```yaml
services:
  converter-ui:
    image: ghcr.io/d4rk-sh4dw/docmost_markdown_converter-ui:latest
    environment:
      - DOCLING_SERVER_URL=http://docling:8080      # URL zum Docling Server
      - OLLAMA_SERVER_URL=http://ollama:11434       # URL zu Ollama
      - OLLAMA_MODEL=llama3                         # Zu verwendendes KI-Modell
```

## Nutzung

1.  Öffnen Sie `http://localhost:3000`.
2.  Laden Sie Ihre Dokumente via Drag & Drop hoch.
3.  Klicken Sie auf **"Konvertierung starten"**.
4.  Der Prozess läuft sequentiell ab (um Ressourcen zu schonen).
5.  Am Ende erhalten Sie eine `.zip` Datei.

### Import in Docmost

1.  Entpacken Sie das ZIP nicht (oder doch, je nach Import-Art).
2.  Importieren Sie das ZIP in Docmost.
3.  Es wird eine Seite **"Import"** erstellt, die alle Ihre Dokumente als Unterseiten enthält.
