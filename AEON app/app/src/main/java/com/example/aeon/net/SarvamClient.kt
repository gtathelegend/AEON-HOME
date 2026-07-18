package com.example.aeon.net

import android.util.Base64
import com.example.aeon.BuildConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Sarvam Saarika (STT) and Bulbul (TTS).
 *
 * The request shapes here were verified against the live API rather than taken
 * from documentation:
 *
 *   POST https://api.sarvam.ai/speech-to-text
 *     header  api-subscription-key: <key>
 *     multipart field name is "file" -- sending "audio" returns
 *     400 {"error":{"message":"body.file : Field required"}}
 *     -> {"request_id", "transcript", "language_code"}
 *
 *   POST https://api.sarvam.ai/text-to-speech
 *     {"text", "target_language_code", "speaker", "model", "pace"}
 *     -> {"request_id", "audios": ["<base64 wav>"]}
 *
 * Honest scoping: this is a cloud call, so audio leaves the phone. Usage history
 * still never leaves the house -- that lives on the AI PC and nothing in the
 * control loop egresses. Say it that way rather than claiming "fully local".
 */
class SarvamClient(private val apiKey: String = BuildConfig.SARVAM_KEY) {

    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .build()

    val configured: Boolean get() = apiKey.isNotBlank()

    class SarvamException(message: String) : IOException(message)

    /** Audio -> text. `wav` must be a complete RIFF/WAVE payload. */
    fun transcribe(wav: ByteArray, languageCode: String = "en-IN"): String {
        requireKey()

        val body = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            // "file", not "audio" -- verified against the live API.
            .addFormDataPart(
                "file", "speech.wav",
                wav.toRequestBody("audio/wav".toMediaType()),
            )
            .addFormDataPart("model", STT_MODEL)
            .addFormDataPart("language_code", languageCode)
            .build()

        val request = Request.Builder()
            .url("$BASE/speech-to-text")
            .addHeader("api-subscription-key", apiKey)
            .post(body)
            .build()

        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw SarvamException("STT ${response.code}: ${describe(text)}")
            }
            return JSONObject(text).optString("transcript").trim()
        }
    }

    /** Text -> spoken WAV bytes, ready for [com.example.aeon.audio.WavPlayer]. */
    fun synthesize(
        text: String,
        languageCode: String = "en-IN",
        speaker: String = SPEAKER,
    ): ByteArray {
        requireKey()

        val payload = JSONObject()
            .put("text", text)
            .put("target_language_code", languageCode)
            .put("speaker", speaker)
            .put("model", TTS_MODEL)
            .put("pace", 1.0)

        val request = Request.Builder()
            .url("$BASE/text-to-speech")
            .addHeader("api-subscription-key", apiKey)
            .post(payload.toString().toRequestBody("application/json".toMediaType()))
            .build()

        http.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw SarvamException("TTS ${response.code}: ${describe(raw)}")
            }
            val audios = JSONObject(raw).optJSONArray("audios")
                ?: throw SarvamException("TTS response carried no audio")
            if (audios.length() == 0) throw SarvamException("TTS returned an empty audio list")
            return Base64.decode(audios.getString(0), Base64.DEFAULT)
        }
    }

    private fun requireKey() {
        if (!configured) {
            throw SarvamException(
                "No Sarvam key. Add `sarvam.key=...` to local.properties and rebuild."
            )
        }
    }

    /** Surface Sarvam's own error text -- a wrong field name should be obvious. */
    private fun describe(body: String): String = try {
        JSONObject(body).optJSONObject("error")?.optString("message") ?: body.take(180)
    } catch (_: Exception) {
        body.take(180)
    }

    private companion object {
        const val BASE = "https://api.sarvam.ai"
        // saaras:v3 transcribed the probe noticeably better than saarika:v2.5,
        // and saarika is being deprecated.
        const val STT_MODEL = "saaras:v3"
        const val TTS_MODEL = "bulbul:v2"
        const val SPEAKER = "anushka"
    }
}
