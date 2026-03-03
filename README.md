<p align="center">
  <img src="https://raw.githubusercontent.com/JamLaMin/hertek_connect/main/icon.png" width="200">
</p>
# Hertek Connect (Home Assistant)

Home Assistant custom integration for reading installation status and active alerts from **Hertek Connect** (Penta).

## Functionaliteit

- Configuratie via UI (Config Flow)
- Automatische token-handling (ververst ruim voor verloopdatum)
- Adaptieve polling:
  - Normaal: ingesteld interval (default 30s)
  - Bij actieve meldingen: sneller (minimaal 15s)
  - Bij brandmelding: nog sneller (minimaal 10s)
  - Bij fouten: backoff om de API niet te belasten
- Sensors (NL):
  - Hoofdstatus (Normaal / Brandmelding / Storing / Uitgeschakeld / Offline / Onbekend)
  - Verbinding (Online / Offline / Onbekend)
  - Actieve meldingen (aantal)
  - Laatste melding (leesbaar, NL, inclusief Zone)
  - Laatste check-in (timestamp, diagnostisch)
  - Installatie status (raw, diagnostisch)
- Binary sensors (NL):
  - Brandmelding actief
  - Storing actief
  - Uitgeschakeld actief
  - Probleem actief
- Service:
  - `hertek_connect.refresh` om direct te verversen
- Blueprints:
  - Automations voor notificaties bij brandmelding/offline/disablement

## Installatie

### Handmatig

1. Download de ZIP van GitHub en pak uit.
2. Kopieer map:
   - `custom_components/hertek_connect/`
   naar je Home Assistant map:
   - `config/custom_components/hertek_connect/`
3. Herstart Home Assistant.
4. Voeg integratie toe:
   - Instellingen → Apparaten en diensten → Integraties → Toevoegen → **Hertek Connect**

### HACS

1. HACS → Integraties → Custom repository toevoegen (categorie: Integration)
2. Installeer **Hertek Connect**
3. Herstart Home Assistant
4. Voeg integratie toe

## Inloggen en security

Deze integratie gebruikt gebruikersnaam/wachtwoord om een bearer token op te vragen.
Gebruik bij voorkeur een apart (read-only) account.

## Troubleshooting

- Instellingen → Systeem → Logboeken
- Gebruik service `hertek_connect.refresh` om direct te testen
