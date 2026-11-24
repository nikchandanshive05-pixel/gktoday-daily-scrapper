package com.artflow.tablet.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = ProAccentBlue,
    background = ProDarkBackground,
    surface = ProSurface,
    surfaceVariant = ProSurfaceVariant,
    onPrimary = ProTextPrimary,
    onBackground = ProTextPrimary,
    onSurface = ProTextPrimary
)

@Composable
fun ProcreateTabletTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        content = content
    )
}
