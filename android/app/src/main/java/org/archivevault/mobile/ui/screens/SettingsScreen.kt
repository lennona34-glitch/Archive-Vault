package org.archivevault.mobile.ui.screens

import android.os.Build
import android.os.Environment
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Folder
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Smartphone
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.archivevault.mobile.ui.theme.VaultBackground
import org.archivevault.mobile.ui.theme.VaultPrimary
import org.archivevault.mobile.ui.theme.VaultSurface

@Composable
fun SettingsScreen(
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val publicDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
    val downloadPath = java.io.File(publicDir, "ArchiveVault").absolutePath

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(VaultBackground)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text(
            text = "⚙️ Settings & Configuration",
            color = Color.White,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold
        )

        // Storage Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = VaultSurface)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Folder, contentDescription = null, tint = VaultPrimary)
                    Spacer(modifier = Modifier.width(10.dp))
                    Text("Storage Location", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = downloadPath,
                    color = VaultPrimary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    lineHeight = 16.sp
                )
                Text(
                    text = "Saved in your public Android Downloads folder. Instantly visible in your phone's Files and Downloads apps.",
                    color = Color.Gray,
                    fontSize = 11.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }

        // Device Target Card (Pixel OS 13)
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = VaultSurface)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Smartphone, contentDescription = null, tint = VaultPrimary)
                    Spacer(modifier = Modifier.width(10.dp))
                    Text("Device & OS", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Optimized for Pixel OS 13 (Android 13 / API ${Build.VERSION.SDK_INT})",
                    color = Color.LightGray,
                    fontSize = 12.sp
                )
                Text(
                    text = "• Material 3 Dark Palette\n• Foreground download service\n• Lock-screen media player session\n• Touch virtual gamepad for DOSBox",
                    color = Color.Gray,
                    fontSize = 11.sp,
                    lineHeight = 18.sp,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }

        // About Card
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = VaultSurface)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Info, contentDescription = null, tint = VaultPrimary)
                    Spacer(modifier = Modifier.width(10.dp))
                    Text("ArchiveVault Mobile", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Version 1.0.0 — Universal Internet Archive Downloader & Explorer",
                    color = Color.Gray,
                    fontSize = 12.sp
                )
            }
        }
    }
}
