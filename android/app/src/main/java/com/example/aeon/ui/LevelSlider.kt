package com.example.aeon.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import com.example.aeon.ui.theme.Ink
import com.example.aeon.ui.theme.Ink4
import com.example.aeon.ui.theme.Rule

/**
 * A hairline track with a black thumb.
 *
 * Hand-rolled rather than Material3's Slider, which brings its own colour
 * treatment, tick marks and elevation. This is one rule and one dot, which is
 * what the rest of the design is made of.
 *
 * [onDrag] fires continuously so the label tracks the thumb; [onCommit] fires
 * once on release, so a drag across the range sends one command instead of
 * forty.
 */
@Composable
fun LevelSlider(
    value: Double,
    lo: Double,
    hi: Double,
    enabled: Boolean = true,
    onDrag: (Double) -> Unit,
    onCommit: (Double) -> Unit,
) {
    val span = (hi - lo).takeIf { it > 0.0 } ?: 1.0
    val thumb = 18.dp

    BoxWithConstraints(
        modifier = Modifier
            .fillMaxWidth()
            .height(thumb),
    ) {
        val widthPx = with(LocalDensity.current) { maxWidth.toPx() }
        val thumbPx = with(LocalDensity.current) { thumb.toPx() }
        val travel = (widthPx - thumbPx).coerceAtLeast(1f)

        // Local position in pixels, seeded from the incoming value.
        var pos by remember(value, widthPx) {
            mutableFloatStateOf((((value - lo) / span).toFloat()).coerceIn(0f, 1f) * travel)
        }

        fun toValue(px: Float): Double = lo + (px / travel).coerceIn(0f, 1f) * span

        Box(
            Modifier
                .fillMaxWidth()
                .height(2.dp)
                .align(Alignment.CenterStart)
                .background(Rule)
        )
        Box(
            Modifier
                .width(with(LocalDensity.current) { (pos + thumbPx / 2).toDp() })
                .height(2.dp)
                .align(Alignment.CenterStart)
                .background(if (enabled) Ink else Ink4)
        )

        // The tap layer goes UNDER the thumb. Above it, it swallows the thumb's
        // own drag gestures and the slider can only be tapped, never dragged.
        Box(
            Modifier
                .fillMaxWidth()
                .height(thumb)
                .pointerInput(enabled, travel) {
                    if (!enabled) return@pointerInput
                    detectTapGestures { offset ->
                        pos = (offset.x - thumbPx / 2).coerceIn(0f, travel)
                        onDrag(toValue(pos))
                        onCommit(toValue(pos))
                    }
                }
        )

        Box(
            Modifier
                .offset { IntOffset(pos.toInt(), 0) }
                .size(thumb)
                .clip(CircleShape)
                .background(if (enabled) Ink else Ink4)
                .pointerInput(enabled, travel) {
                    if (!enabled) return@pointerInput
                    detectHorizontalDragGestures(
                        onDragEnd = { onCommit(toValue(pos)) },
                        onDragCancel = { onCommit(toValue(pos)) },
                    ) { change, delta ->
                        change.consume()
                        pos = (pos + delta).coerceIn(0f, travel)
                        onDrag(toValue(pos))
                    }
                }
        )
    }
}
