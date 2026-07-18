package com.example.aeon.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.concurrent.thread

/**
 * Microphone -> a complete WAV file in memory.
 *
 * Sarvam's STT endpoint takes a multipart file, so the recording has to be a
 * real RIFF/WAVE payload, not bare PCM: raw samples are accepted by the upload
 * and then transcribe to nothing, which looks like a bad microphone rather than
 * a missing 44-byte header.
 */
class WavRecorder(
    private val sampleRate: Int = 16_000,
) {
    @Volatile private var recording = false
    private var recorder: AudioRecord? = null
    private var worker: Thread? = null
    private val buffer = ByteArrayOutputStream()

    val isRecording: Boolean get() = recording

    @SuppressLint("MissingPermission")   // caller holds RECORD_AUDIO; checked in the UI
    @Throws(IOException::class)
    fun start() {
        if (recording) return

        val minBuffer = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
        )
        if (minBuffer <= 0) throw IOException("this device cannot record 16 kHz mono PCM")

        // A generous buffer: an under-sized one drops samples under UI load and
        // the transcript comes back clipped.
        val bufferSize = minBuffer * 4

        val record = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize,
        )
        if (record.state != AudioRecord.STATE_INITIALIZED) {
            record.release()
            throw IOException("microphone unavailable - is another app holding it?")
        }

        buffer.reset()
        recorder = record
        recording = true
        record.startRecording()

        worker = thread(isDaemon = true, name = "aeon-mic") {
            val chunk = ByteArray(bufferSize)
            while (recording) {
                val read = record.read(chunk, 0, chunk.size)
                if (read > 0) synchronized(buffer) { buffer.write(chunk, 0, read) }
            }
        }
    }

    /** Stop and return the WAV, or null if nothing usable was captured. */
    fun stop(): ByteArray? {
        if (!recording) return null
        recording = false

        worker?.join(1_000)
        worker = null

        recorder?.run {
            try {
                stop()
            } catch (_: IllegalStateException) {
                // Already stopped; releasing is still the right move.
            }
            release()
        }
        recorder = null

        val pcm = synchronized(buffer) { buffer.toByteArray() }
        // Under ~0.2 s is a mis-tap, not speech. Sending it wastes a round trip
        // and comes back as an empty transcript.
        if (pcm.size < sampleRate / 5) return null
        return wrapAsWav(pcm)
    }

    fun cancel() {
        recording = false
        worker?.join(500)
        worker = null
        recorder?.run {
            try {
                stop()
            } catch (_: IllegalStateException) {
            }
            release()
        }
        recorder = null
        synchronized(buffer) { buffer.reset() }
    }

    private fun wrapAsWav(pcm: ByteArray): ByteArray {
        val channels = 1
        val bitsPerSample = 16
        val byteRate = sampleRate * channels * bitsPerSample / 8
        val blockAlign = channels * bitsPerSample / 8

        val header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        header.put("RIFF".toByteArray(Charsets.US_ASCII))
        header.putInt(36 + pcm.size)
        header.put("WAVE".toByteArray(Charsets.US_ASCII))
        header.put("fmt ".toByteArray(Charsets.US_ASCII))
        header.putInt(16)                       // PCM fmt chunk size
        header.putShort(1)                      // format = PCM
        header.putShort(channels.toShort())
        header.putInt(sampleRate)
        header.putInt(byteRate)
        header.putShort(blockAlign.toShort())
        header.putShort(bitsPerSample.toShort())
        header.put("data".toByteArray(Charsets.US_ASCII))
        header.putInt(pcm.size)

        return header.array() + pcm
    }
}
