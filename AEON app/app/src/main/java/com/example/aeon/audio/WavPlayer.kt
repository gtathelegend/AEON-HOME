package com.example.aeon.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.MediaPlayer
import java.io.File

/**
 * Plays the WAV that Bulbul returns.
 *
 * Via a cache file and MediaPlayer rather than AudioTrack: Bulbul picks its own
 * sample rate, and MediaPlayer reads that from the header instead of making us
 * parse it and get chipmunk audio when the default is wrong.
 */
class WavPlayer(private val context: Context) {

    private var player: MediaPlayer? = null

    fun play(wav: ByteArray, onDone: () -> Unit = {}) {
        stop()
        val file = File(context.cacheDir, "aeon-tts.wav").apply { writeBytes(wav) }

        player = MediaPlayer().apply {
            setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANT)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            setDataSource(file.absolutePath)
            setOnCompletionListener {
                it.release()
                player = null
                file.delete()
                onDone()
            }
            setOnErrorListener { mp, _, _ ->
                mp.release()
                player = null
                file.delete()
                onDone()
                true
            }
            prepare()
            start()
        }
    }

    fun stop() {
        player?.run {
            try {
                if (isPlaying) stop()
            } catch (_: IllegalStateException) {
            }
            release()
        }
        player = null
    }
}
