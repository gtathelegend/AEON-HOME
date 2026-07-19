package com.example.aeon.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// Deliberately light-only, and no dynamic colour. The design is a white page
// with black ink; following the system into dark mode or picking up the user's
// wallpaper palette would produce a different product, not a variant of this one.
private val AeonColors = lightColorScheme(
    primary = Ink,
    onPrimary = Ground,
    secondary = Ink2,
    onSecondary = Ground,
    background = Ground,
    onBackground = Ink,
    surface = Ground,
    onSurface = Ink,
    surfaceVariant = Wash,
    onSurfaceVariant = Ink2,
    outline = Rule2,
    outlineVariant = Rule,
    error = Ink,
    onError = Ground,
)

@Composable
fun AEONTheme(
    @Suppress("UNUSED_PARAMETER") darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            val controller = WindowCompat.getInsetsController(window, view)
            // Dark icons on a white bar. Without this the status bar icons are
            // white on white and simply vanish.
            controller.isAppearanceLightStatusBars = true
            controller.isAppearanceLightNavigationBars = true
        }
    }

    MaterialTheme(
        colorScheme = AeonColors,
        typography = AeonTypography,
        content = content,
    )
}
