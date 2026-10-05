package org.archivevault.mobile.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

val VaultBackground = Color(0xFF09090B)
val VaultSurface = Color(0xFF141417)
val VaultSurfaceVariant = Color(0xFF27272A)
val VaultPrimary = Color(0xFF38BDF8)
val VaultSecondary = Color(0xFF10B981)
val VaultAccent = Color(0xFF6366F1)
val VaultTextPrimary = Color(0xFFF4F4F5)
val VaultTextSecondary = Color(0xFFA1A1AA)

private val DarkColorScheme = darkColorScheme(
    primary = VaultPrimary,
    secondary = VaultSecondary,
    tertiary = VaultAccent,
    background = VaultBackground,
    surface = VaultSurface,
    surfaceVariant = VaultSurfaceVariant,
    onBackground = VaultTextPrimary,
    onSurface = VaultTextPrimary,
    onPrimary = Color.Black,
    onSecondary = Color.Black
)

@Composable
fun ArchiveVaultTheme(
    darkTheme: Boolean = true,
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            dynamicDarkColorScheme(context)
        }
        else -> DarkColorScheme
    }

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = VaultBackground.toArgb()
            window.navigationBarColor = VaultBackground.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
            WindowCompat.getInsetsController(window, view).isAppearanceLightNavigationBars = false
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
