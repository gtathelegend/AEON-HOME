# ÆON Home — Android app

The phone half of [ÆON Home](../README.md). Speak a preference once; the central
node switches the appliance immediately and the AI PC learns it.

White ground, black ink, monospace — the same restraint as the PC dashboard, so
the two screens read as one system.

## What it does

- **Hold to speak.** Records 16 kHz mono WAV, transcribes with **Sarvam Saaras**,
  sends the sentence to the hub, and confirms aloud with **Sarvam Bulbul**.
- **Tiles and sliders** for direct control, with line-art images of each
  appliance.
- **Learned** panel — what the house has been told, straight from the hub.
- Reads the **same WebSocket** the browser client uses, so the phone and the PC
  dashboard cannot disagree.

The phone talks to the **central node**, never to the PC. Close the laptop and
the app still works.

## Setup

1. Open this folder in Android Studio (it is a standalone Gradle project).
2. Copy `local.properties.example` to `local.properties` and add your Sarvam key:

   ```properties
   sarvam.key=sk_your_key_here
   ```

   Get one at [dashboard.sarvam.ai](https://dashboard.sarvam.ai). The app builds
   and runs **without** a key — the mic is disabled, everything else works.

3. Run the hub on the AI PC (`python run.py` in the parent folder). It prints a
   phone URL like `http://192.168.1.42:8800/phone` — the IP in that URL is the
   hub address.
4. Build and install:

   ```bash
   ./gradlew installDebug
   ```

5. Launch the app, tap **HUB**, enter that IP and port `8800`, and Connect.
   The address is remembered.

Both devices must be on the same WiFi. No account, no pairing, no cloud
service in the control loop.

## Try it

- *"Set the AC to 25 degrees at 9 PM"*
- *"Run the fan at full speed at 3 PM"*
- *"Night light at 11 PM"*
- *"AC ko 23 degree pe chalao 9 baje"* — code-mixed Hindi/English

Each sentence should appear on the PC dashboard's live log within a millisecond
or two of the appliance changing.

## The Sarvam contract

Verified against the live API rather than taken from docs, because the published
reference is JavaScript-rendered and did not fetch cleanly:

| | |
|---|---|
| Auth header | `api-subscription-key` |
| STT | `POST https://api.sarvam.ai/speech-to-text` |
| STT body | multipart; the file field is **`file`** (`audio` returns `400 body.file : Field required`) |
| STT response | `{request_id, transcript, language_code}` |
| TTS | `POST https://api.sarvam.ai/text-to-speech` |
| TTS body | `{text, target_language_code, speaker, model, pace}` |
| TTS response | `{request_id, audios: ["<base64 wav>"]}` |

Models: `saaras:v3` for STT (it transcribed the probe noticeably better than
`saarika:v2.5`, which is being deprecated), `bulbul:v2` with speaker `anushka`
for TTS.

To change any of this, edit the companion object at the bottom of
[`SarvamClient.kt`](app/src/main/java/com/example/aeon/net/SarvamClient.kt) —
it is the only place these strings appear, and API errors are surfaced verbatim
in the app so a wrong value is immediately diagnosable.

## Privacy, stated honestly

Usage history never leaves your home — that lives in SQLite on the AI PC, and
nothing in the control loop egresses. **The voice channel is different:** Sarvam
STT/TTS are cloud calls, so recorded audio does leave the phone. That is an
opt-in cloud call, not a local one, and the app is useful with the mic switched
off entirely.

If Sarvam's on-device path is used instead, the claim strengthens to "nothing
leaves the phone at all". State whichever is true on the day.

## Security note

**Never commit `local.properties`.** It is gitignored, and the hackathon requires
a public repository. A key in public source is a key that has to be rotated.

## Layout

| File | Role |
|---|---|
| `MainActivity.kt` | permission flow — the mic is requested when you press it, not at launch |
| `AeonViewModel.kt` | speech → hub → spoken confirmation |
| `net/HubClient.kt` | the hub WebSocket, with reconnect |
| `net/SarvamClient.kt` | Saaras STT and Bulbul TTS |
| `audio/WavRecorder.kt` | AudioRecord → a real RIFF/WAVE payload |
| `audio/WavPlayer.kt` | plays the WAV Bulbul returns |
| `ui/AeonScreen.kt` | the single screen |
| `ui/LevelSlider.kt` | hairline track, black thumb |
| `model/HubModels.kt` | mirrors `HubState.snapshot()` |
