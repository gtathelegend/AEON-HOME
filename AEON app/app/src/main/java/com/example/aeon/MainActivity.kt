package com.example.aeon

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.aeon.ui.AeonScreen
import com.example.aeon.ui.theme.AEONTheme

class MainActivity : ComponentActivity() {

    private var onMicGranted: (() -> Unit)? = null

    private val requestMic = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) onMicGranted?.invoke()
        onMicGranted = null
    }

    private fun withMicPermission(block: () -> Unit) {
        val granted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED

        if (granted) {
            block()
        } else {
            // Deliberately not requested at launch. Asking for a microphone
            // before the user has tried to speak reads as a grab; asking when
            // they press the mic reads as the reason they pressed it.
            onMicGranted = block
            requestMic.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AEONTheme {
                val vm: AeonViewModel = viewModel()
                val state by vm.ui.collectAsState()

                Scaffold(modifier = Modifier.fillMaxSize()) { insets ->
                    AeonScreen(
                        state = state,
                        onMicDown = { withMicPermission { vm.startListening() } },
                        onMicUp = { vm.stopListeningAndSend() },
                        onSend = vm::send,
                        onToggle = vm::toggle,
                        onLevel = vm::setLevel,
                        onDismissNotice = vm::dismissNotice,
                        modifier = Modifier.padding(insets),
                    )
                }
            }
        }
    }
}
