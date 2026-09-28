# Offline / restricted network

On a connected approved builder, use the same platform/architecture and Ollama release as the Ministry target. Run `scripts/prepare_offline_bundle.sh`; it pulls/builds required runtime images, saves images, copies Ollama model store, and writes SHA-256 records under `assets/offline/`. Transfer only the deployment folder via approved media. Generate fresh Ministry `.env` on target; never transfer builder credentials, WhatsApp auth or DB data.

Ministry IT must separately provide trusted Ubuntu/Docker/NVIDIA packages from its mirror. On target: verify checksums, install driver/Docker/toolkit, create `.env`, then `scripts/install_offline.sh`. Confirm `ollama list` and successful Arabic generation; the store import path is same-version dependent. Offline build/import was not executed on Ubuntu; validate it on a disconnected staging host first. Fonts and chart.js are external CDN references in the dashboard HTML, so charts/fonts may be unavailable without network; fully air-gapped browser asset vendoring remains a blocker.

Scraper output (`data/final/*.json`) is runtime data in the `source-data` volume, produced by `scripts/refresh_sources.sh`; it is never part of the Git tree or image build context. `scripts/install_offline.sh` sets `NEXASERVE_OFFLINE=1` so every compose call adds the offline overlay.
