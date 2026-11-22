package com.antigravity.mobile.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

val PrimaryPurple = Color(0xFF7C3AED)
val ElectricCyan = Color(0xFF06B6D4)
val DarkBackground = Color(0xFF0F172A)
val SurfaceDark = Color(0xFF1E293B)
val UserBubbleDark = Color(0xFF334155)
val AgentText = Color(0xFFF1F5F9)
val ToolCardBg = Color(0xFF0B132B)
val ApprovedGreen = Color(0xFF10B981)
val DeniedRed = Color(0xFFEF4444)

private val DarkColorScheme = darkColorScheme(
    primary = PrimaryPurple,
    secondary = ElectricCyan,
    background = DarkBackground,
    surface = SurfaceDark,
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onBackground = AgentText,
    onSurface = AgentText
)

private val LightColorScheme = lightColorScheme(
    primary = PrimaryPurple,
    secondary = ElectricCyan,
    background = Color(0xFFF8FAFC),
    surface = Color.White,
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onBackground = Color(0xFF0F172A),
    onSurface = Color(0xFF0F172A)
)

@Composable
fun AntigravityTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
