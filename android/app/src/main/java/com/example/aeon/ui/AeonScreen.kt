package com.example.aeon.ui

import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.example.aeon.Mic
import com.example.aeon.R
import com.example.aeon.UiState
import com.example.aeon.model.DeviceState
import com.example.aeon.ui.theme.Ground
import com.example.aeon.ui.theme.Ink
import com.example.aeon.ui.theme.Ink3
import com.example.aeon.ui.theme.Ink4
import com.example.aeon.ui.theme.Rule
import com.example.aeon.ui.theme.Rule2
import com.example.aeon.ui.theme.Wash

@Composable
fun AeonScreen(
    state: UiState,
    onMicDown: () -> Unit,
    onMicUp: () -> Unit,
    onSend: (String) -> Unit,
    onToggle: (String, Boolean, Double?) -> Unit,
    onLevel: (String, Double) -> Unit,
    onSetHub: (String, Int) -> Unit,
    onToggleSettings: () -> Unit,
    onLocate: () -> Unit,
    onDismissNotice: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Ground)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 22.dp)
            .padding(top = 18.dp, bottom = 36.dp),
        verticalArrangement = Arrangement.spacedBy(22.dp),
    ) {
        Header(state, onToggleSettings)

        if (state.showSettings) {
            HubSettings(state, onSetHub, onLocate)
        }

        state.notice?.let { Notice(it, onDismissNotice) }

        MicBlock(state, onMicDown, onMicUp)

        TypeRow(onSend)

        val devices = state.snapshot?.devices.orEmpty()
        if (devices.isEmpty()) {
            Placeholder(state)
        } else {
            Label("Devices")
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                devices.forEach { device ->
                    DeviceCard(device, onToggle, onLevel)
                }
            }
        }

        val learned = state.snapshot?.learned.orEmpty()
        if (learned.isNotEmpty()) {
            Label("Learned")
            Column {
                learned.forEach { row ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 9.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(row.text, style = MaterialTheme.typography.bodyMedium, color = Ink)
                        Text(row.label, style = MaterialTheme.typography.labelSmall, color = Ink3)
                    }
                    Divider()
                }
            }
        }

        state.snapshot?.let { snap ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("MODEL v${snap.modelVersion}",
                    style = MaterialTheme.typography.labelSmall, color = Ink3)
                Text("CLOUD BYTES ${snap.cloudBytes}",
                    style = MaterialTheme.typography.labelSmall, color = Ink3)
            }
        }
    }
}

// ── header ───────────────────────────────────────────────────────────────

@Composable
private fun Header(state: UiState, onToggleSettings: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("ÆON HOME", style = MaterialTheme.typography.titleMedium, color = Ink)

        Row(verticalAlignment = Alignment.CenterVertically) {
            Dot(filled = state.linked, online = state.linked)
            Spacer(Modifier.width(8.dp))
            Text(
                if (state.linked) state.snapshot?.clock ?: "linked" else state.linkNote,
                style = MaterialTheme.typography.labelSmall,
                color = Ink3,
            )
            Spacer(Modifier.width(12.dp))
            // Always reachable. When the laptop's address changes mid-demo this
            // is the one control that gets you working again.
            TextButton(
                onClick = onToggleSettings,
                contentPadding = androidx.compose.foundation.layout.PaddingValues(4.dp),
            ) {
                Text("HUB", style = MaterialTheme.typography.labelSmall, color = Ink)
            }
        }
    }
}

@Composable
private fun HubSettings(
    state: UiState,
    onSetHub: (String, Int) -> Unit,
    onLocate: () -> Unit,
) {
    var host by remember(state.host) { mutableStateOf(state.host) }
    var port by remember(state.port) { mutableStateOf(state.port.toString()) }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Rule2, RoundedCornerShape(2.dp))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Label("Hub address")
        Text(
            "The address the hub prints on the PC when it starts. " +
                "Phone and PC on the same WiFi; no pairing, no account.",
            style = MaterialTheme.typography.bodyMedium,
            color = Ink3,
        )
        // This phone's own address, next to the one being typed. If they do not
        // share a subnet the two devices are not on the same network, and that
        // is visible here instead of after six seconds of timeout.
        Text(
            "this phone: ${state.selfAddress}",
            style = MaterialTheme.typography.labelSmall,
            color = if (state.selfAddress.startsWith("mobile") ||
                state.selfAddress == "no network") Ink else Ink3,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedTextField(
                value = host,
                onValueChange = { host = it },
                placeholder = { Text("192.168.1.42", color = Ink4) },
                singleLine = true,
                modifier = Modifier.weight(2f),
                textStyle = MaterialTheme.typography.bodyLarge,
            )
            OutlinedTextField(
                value = port,
                onValueChange = { port = it.filter(Char::isDigit).take(5) },
                singleLine = true,
                modifier = Modifier.weight(1f),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                textStyle = MaterialTheme.typography.bodyLarge,
            )
        }
        BlockButton("Connect") { onSetHub(host, port.toIntOrNull() ?: 8800) }
        // Offered, not relied on: it fills the field in and the user still
        // presses Connect. On a phone that has fallen back to mobile data it
        // finds nothing, and a typed address still works.
        TextButton(
            onClick = onLocate,
            contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
        ) {
            Text(
                if (state.searching) "SEARCHING…" else "FIND ON THIS WIFI",
                style = MaterialTheme.typography.labelSmall,
                color = if (state.searching) Ink3 else Ink,
            )
        }
    }
}


@Composable
private fun Notice(text: String, onDismiss: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Wash)
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(text, style = MaterialTheme.typography.bodyMedium, color = Ink)
        TextButton(onClick = onDismiss, contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
            Text("DISMISS", style = MaterialTheme.typography.labelSmall, color = Ink)
        }
    }
}

// ── mic ──────────────────────────────────────────────────────────────────

@Composable
private fun MicBlock(state: UiState, onDown: () -> Unit, onUp: () -> Unit) {
    val listening = state.mic == Mic.Listening
    val pulse = rememberInfiniteTransition(label = "mic")
    val ring by pulse.animateFloat(
        initialValue = 0f,
        targetValue = if (listening) 1f else 0f,
        animationSpec = infiniteRepeatable(tween(1400)),
        label = "ring",
    )

    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Box(contentAlignment = Alignment.Center) {
            if (listening) {
                Box(
                    Modifier
                        .size((132f + ring * 26f).dp)
                        .alpha(0.10f * (1f - ring))
                        .clip(CircleShape)
                        .background(Ink)
                )
            }
            Box(
                modifier = Modifier
                    .size(132.dp)
                    .clip(CircleShape)
                    .background(if (listening) Ink else Ground)
                    .border(1.dp, if (listening) Ink else Rule2, CircleShape)
                    // Tap to start, tap again to stop and send -- not hold.
                    // Holding a phone against your ear for the length of a
                    // sentence is fine; holding a finger perfectly still on a
                    // button while you think of the words is not, and letting go
                    // early truncates the recording with no way to recover it.
                    // A tap in Thinking state is ignored: both handlers guard on
                    // the current mic state.
                    .pointerInput(state.mic) {
                        detectTapGestures(
                            onTap = { if (listening) onUp() else onDown() }
                        )
                    },
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_mic),
                    contentDescription = if (listening) "Tap to stop and send" else "Tap to speak",
                    tint = if (listening) Ground else Ink,
                    modifier = Modifier.size(34.dp),
                )
            }
        }

        Text(
            when {
                state.mic == Mic.Listening -> "Listening… tap to stop and send"
                state.mic == Mic.Thinking -> "Transcribing…"
                state.heard.isNotBlank() -> "“${state.heard}”"
                else -> "Tap to speak"
            },
            style = MaterialTheme.typography.bodyLarge,
            color = if (state.heard.isNotBlank() && state.mic == Mic.Idle) Ink else Ink3,
        )

        if (state.heard.isBlank() && state.mic == Mic.Idle) {
            Text(
                "“Set the AC to 25 degrees at 9 PM”",
                style = MaterialTheme.typography.bodyMedium,
                color = Ink4,
            )
        }
    }
}

// ── typed fallback ───────────────────────────────────────────────────────

@Composable
private fun TypeRow(onSend: (String) -> Unit) {
    var text by remember { mutableStateOf("") }

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            placeholder = {
                Text("or type it — AC ko 23 degree pe chalao", color = Ink4,
                    style = MaterialTheme.typography.bodyMedium)
            },
            singleLine = true,
            modifier = Modifier.weight(1f),
            textStyle = MaterialTheme.typography.bodyLarge,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
            keyboardActions = KeyboardActions(onSend = {
                onSend(text); text = ""
            }),
        )
        BlockButton("Send") { onSend(text); text = "" }
    }
}

// ── device card ──────────────────────────────────────────────────────────

@Composable
private fun DeviceCard(
    device: DeviceState,
    onToggle: (String, Boolean, Double?) -> Unit,
    onLevel: (String, Double) -> Unit,
) {
    // Track the thumb locally while dragging so incoming snapshots do not fight
    // the user's finger, then commit once on release.
    var dragging by remember { mutableStateOf(false) }
    var draft by remember(device.level) { mutableStateOf(device.level ?: device.rangeLo) }

    val shown = if (dragging) draft else (device.level ?: device.rangeLo)
    val border by animateFloatAsState(if (device.on) 1f else 0f, label = "border")

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .border(
                1.dp,
                lerpColor(Rule2, Ink, border),
                RoundedCornerShape(2.dp),
            )
            .alpha(if (device.online) 1f else 0.45f)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                painter = painterResource(iconFor(device.id)),
                contentDescription = null,
                tint = if (device.on) Ink else Ink4,
                modifier = Modifier.size(30.dp),
            )
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(device.label, style = MaterialTheme.typography.labelSmall, color = Ink3)
                Text(
                    if (device.online) {
                        if (device.on) formatLevel(device, shown) else "OFF"
                    } else "OFFLINE",
                    style = MaterialTheme.typography.headlineMedium,
                    color = if (device.on) Ink else Ink4,
                )
            }
            PowerButton(device.on) {
                onToggle(device.id, !device.on, device.level ?: device.rangeHi)
            }
        }

        LevelSlider(
            value = shown,
            lo = device.rangeLo,
            hi = device.rangeHi,
            enabled = device.online,
            onDrag = { dragging = true; draft = it },
            onCommit = { dragging = false; onLevel(device.id, it) },
        )

        // Three decimals, not two. Confidence is 0.65*|p_on-0.5|*2 + 0.35, so a
        // decisive model sits around 0.998 and genuinely moves in the third
        // decimal -- rounding to two flattened every device to a motionless
        // "1.00" that read as a printed label rather than a live figure.
        Text(
            when {
                !device.online -> "leaf unreachable"
                device.gate == "held" ->
                    "connected · held · ${"%.3f".format(device.confidence)}"
                else ->
                    "connected · ${device.source} · ${"%.3f".format(device.confidence)}"
            },
            style = MaterialTheme.typography.labelSmall,
            color = Ink3,
        )
    }
}

@Composable
private fun PowerButton(on: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(2.dp))
            .background(if (on) Ink else Ground)
            .border(1.dp, if (on) Ink else Rule2, RoundedCornerShape(2.dp))
            .pointerInput(on) { detectTapGestures { onClick() } }
            .padding(horizontal = 16.dp, vertical = 9.dp),
    ) {
        Text(
            if (on) "ON" else "OFF",
            style = MaterialTheme.typography.labelSmall,
            color = if (on) Ground else Ink,
        )
    }
}

// ── bits ─────────────────────────────────────────────────────────────────

@Composable
private fun Placeholder(state: UiState) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Rule, RoundedCornerShape(2.dp))
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            if (state.host.isBlank()) "No hub address set." else "Waiting for the hub…",
            style = MaterialTheme.typography.bodyLarge,
            color = Ink,
        )
        Text(
            if (state.host.isBlank())
                "Tap HUB and enter the address the hub printed on the PC."
            else
                "${state.host}:${state.port} — ${state.linkNote}",
            style = MaterialTheme.typography.bodyMedium,
            color = Ink3,
        )
    }
}

@Composable
private fun Label(text: String) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = Ink3)
}

@Composable
private fun Divider() {
    Box(
        Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(Rule)
    )
}

@Composable
private fun Dot(filled: Boolean, online: Boolean) {
    Box(
        Modifier
            .size(8.dp)
            .clip(CircleShape)
            .background(if (filled) Ink else Ground)
            .border(1.dp, if (online) Ink else Ink4, CircleShape)
    )
}

@Composable
private fun BlockButton(text: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(2.dp))
            .border(1.dp, Rule2, RoundedCornerShape(2.dp))
            .pointerInput(Unit) { detectTapGestures { onClick() } }
            .padding(horizontal = 18.dp, vertical = 14.dp),
    ) {
        Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = Ink)
    }
}

// Matched on the device-family prefix, so appending a device to DEVICE_ORDER
// needs one line here and nothing else. The vacuum previously fell through to
// the bulb: a robot vacuum drawn as a light bulb is not a cosmetic problem, it
// is the screen telling the user the wrong thing about their house.
private fun iconFor(deviceId: String): Int = when {
    deviceId.startsWith("ac") -> R.drawable.ic_ac
    deviceId.startsWith("fan") -> R.drawable.ic_fan
    deviceId.startsWith("vacuum") -> R.drawable.ic_vacuum
    else -> R.drawable.ic_bulb
}

private fun formatLevel(device: DeviceState, value: Double): String = when (device.unit) {
    "K" -> "${value.toInt()}K"
    "%" -> "${value.toInt()}%"
    else -> "%.1f%s".format(value, device.unit)
}

private fun lerpColor(from: Color, to: Color, t: Float): Color = Color(
    red = from.red + (to.red - from.red) * t,
    green = from.green + (to.green - from.green) * t,
    blue = from.blue + (to.blue - from.blue) * t,
    alpha = 1f,
)
