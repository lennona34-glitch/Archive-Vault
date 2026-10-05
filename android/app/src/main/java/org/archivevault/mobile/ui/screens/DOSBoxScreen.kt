package org.archivevault.mobile.ui.screens

import android.annotation.SuppressLint
import android.content.res.Configuration
import android.view.View
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Gamepad
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import org.archivevault.mobile.input.GameInputHandler
import org.archivevault.mobile.ui.components.VirtualGamepadDock
import org.archivevault.mobile.ui.theme.VaultPrimary
import org.archivevault.mobile.ui.theme.VaultSecondary
import org.archivevault.mobile.ui.theme.VaultSurface

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun DOSBoxScreen(
    identifier: String,
    title: String,
    inputHandler: GameInputHandler,
    onClose: () -> Unit,
    modifier: Modifier = Modifier
) {
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var isGamepadVisible by remember { mutableStateOf(true) }
    var isGameReady by remember { mutableStateOf(false) }

    val configuration = LocalConfiguration.current
    val isLandscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    // Safe full shutdown of emulation and audio
    val handleClose: () -> Unit = {
        try {
            webViewRef?.apply {
                stopLoading()
                loadUrl("about:blank")
                onPause()
                pauseTimers()
                destroy()
            }
        } catch (_: Exception) {}
        webViewRef = null
        inputHandler.unbind()
        onClose()
    }

    // Intercept hardware Android back button to prevent background audio leaks
    BackHandler {
        handleClose()
    }

    DisposableEffect(Unit) {
        onDispose {
            try {
                webViewRef?.apply {
                    stopLoading()
                    loadUrl("about:blank")
                    onPause()
                    pauseTimers()
                    destroy()
                }
            } catch (_: Exception) {}
            webViewRef = null
            inputHandler.unbind()
        }
    }

    val arcadeScript = """
        (function() {
            // 1. Force and pin viewport to top-left (0, 0)
            window.scrollTo(0, 0);
            if (document.documentElement) document.documentElement.scrollTop = 0;
            if (document.body) document.body.scrollTop = 0;

            // 2. Lock scroll APIs completely
            window.scrollTo = function() { return false; };
            window.scroll = function() { return false; };
            window.scrollBy = function() { return false; };
            Element.prototype.scrollIntoView = function() { return false; };

            // 3. Prevent anchor jump on #loading
            var btn = document.getElementById('jsmessSS');
            if (btn) {
                btn.removeAttribute('href');
                btn.setAttribute('href', 'javascript:void(0)');
            }

            var el = document.getElementById('av-arcade-style');
            if (!el) {
                var s = document.createElement('style');
                s.id = 'av-arcade-style';
                s.textContent = [
                    'html, body {',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    margin: 0 !important;',
                    '    padding: 0 !important;',
                    '    overflow: hidden !important;',
                    '    position: fixed !important;',
                    '    top: 0 !important;',
                    '    left: 0 !important;',
                    '    right: 0 !important;',
                    '    bottom: 0 !important;',
                    '    background: #000000 !important;',
                    '}',
                    '#wrap, #theatre-ia-wrap, #emulate, .ia-module {',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    margin: 0 !important;',
                    '    padding: 0 !important;',
                    '    background: #000000 !important;',
                    '    position: absolute !important;',
                    '    top: 0 !important;',
                    '    left: 0 !important;',
                    '    right: 0 !important;',
                    '    bottom: 0 !important;',
                    '    display: flex !important;',
                    '    justify-content: center !important;',
                    '    align-items: center !important;',
                    '    transform: none !important;',
                    '    -webkit-transform: none !important;',
                    '}',
                    '#canvasholder {',
                    '    position: absolute !important;',
                    '    top: 0 !important;',
                    '    left: 0 !important;',
                    '    right: 0 !important;',
                    '    bottom: 0 !important;',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    display: flex !important;',
                    '    justify-content: center !important;',
                    '    align-items: center !important;',
                    '    margin: 0 !important;',
                    '    padding: 0 !important;',
                    '    background: #000000 !important;',
                    '    z-index: 2 !important;',
                    '    transform: none !important;',
                    '    -webkit-transform: none !important;',
                    '}',
                    '#canvas {',
                    '    max-width: 100% !important;',
                    '    max-height: 100% !important;',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    object-fit: contain !important;',
                    '    margin: auto !important;',
                    '    position: relative !important;',
                    '    top: 0 !important;',
                    '    left: 0 !important;',
                    '    transform: none !important;',
                    '    -webkit-transform: none !important;',
                    '    image-rendering: pixelated !important;',
                    '    image-rendering: crisp-edges !important;',
                    '}',
                    '/* Hide the clunky Archive.org screenshot and power button completely */',
                    '#jsmessSS {',
                    '    position: absolute !important;',
                    '    top: 0 !important;',
                    '    left: 0 !important;',
                    '    width: 100% !important;',
                    '    height: 100% !important;',
                    '    opacity: 0 !important;',
                    '    z-index: 10 !important;',
                    '    cursor: pointer !important;',
                    '    display: flex !important;',
                    '    flex-direction: column !important;',
                    '    justify-content: center !important;',
                    '    align-items: center !important;',
                    '    background: #000000 !important;',
                    '}',
                    '#jsmessSS.av-started {',
                    '    display: none !important;',
                    '    visibility: hidden !important;',
                    '    pointer-events: none !important;',
                    '}',
                    '.emularity-splash-screen, .emularity-splash {',
                    '    position: absolute !important;',
                    '    top: 50% !important;',
                    '    left: 50% !important;',
                    '    transform: translate(-50%, -50%) !important;',
                    '    width: 90% !important;',
                    '    max-width: 400px !important;',
                    '    z-index: 8 !important;',
                    '    color: #38bdf8 !important;',
                    '    text-align: center !important;',
                    '    font-family: monospace !important;',
                    '}',
                    '.hidden-for-screen-readers, .navia-header, .ia-topnav, #theatre-controls, #theatre-ia-wrap .theater-controls {',
                    '    display: none !important;',
                    '}'
                ].join('\n');
                document.head.appendChild(s);
            }

            window.__av_boot = function() {
                var btn = document.getElementById('jsmessSS');
                var ghost = document.querySelector('#jsmessSS img.ghost');
                var can = document.getElementById('canvas');

                if (btn && btn.getAttribute('href') !== 'javascript:void(0)') {
                    btn.removeAttribute('href');
                    btn.setAttribute('href', 'javascript:void(0)');
                }

                window.scrollTo(0, 0);
                if (document.documentElement) document.documentElement.scrollTop = 0;
                if (document.body) document.body.scrollTop = 0;

                // Detect when DOS game resolution is active (e.g. 320x200, 640x400)
                if (can && (can.height > 150 || can.width > 300)) {
                    if (btn) btn.classList.add('av-started');
                    can.style.transform = 'none';
                    can.style.top = '0px';
                    can.style.marginTop = '0px';
                    can.focus();
                    return true;
                }

                // Click the invisible start button behind our native loading screen
                if (btn && btn.offsetParent !== null) {
                    if (ghost) {
                        ghost.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                    }
                    btn.click();
                }
                return false;
            };
        })();
    """.trimIndent()

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            // Arcade Header Bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(if (isLandscape) Color(0xDD141824) else VaultSurface)
                    .statusBarsPadding()
                    .padding(horizontal = 14.dp, vertical = if (isLandscape) 4.dp else 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(Icons.Default.SportsEsports, contentDescription = null, tint = VaultSecondary)
                    Text(
                        text = title,
                        color = Color.White,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1
                    )
                }

                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Controls toggle (hide in landscape or toggle overlay)
                    if (!isLandscape) {
                        IconButton(
                            onClick = { isGamepadVisible = !isGamepadVisible },
                            modifier = Modifier.size(36.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Gamepad,
                                contentDescription = "Toggle Gamepad",
                                tint = if (isGamepadVisible) VaultPrimary else Color.Gray
                            )
                        }
                    }

                    // Restart
                    IconButton(
                        onClick = {
                            isGameReady = false
                            webViewRef?.reload()
                        },
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(Icons.Default.Refresh, contentDescription = "Restart", tint = Color.LightGray)
                    }

                    // Exit
                    IconButton(
                        onClick = handleClose,
                        modifier = Modifier.size(36.dp)
                    ) {
                        Icon(Icons.Default.Close, contentDescription = "Exit", tint = Color(0xFFF43F5E))
                    }
                }
            }

            // Retro Game Canvas Viewport Area (expands to clean full screen in landscape)
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .background(Color.Black)
            ) {
                AndroidView(
                    factory = { context ->
                        WebView(context).apply {
                            layoutParams = ViewGroup.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT
                            )
                            overScrollMode = View.OVER_SCROLL_NEVER
                            isVerticalScrollBarEnabled = false
                            isHorizontalScrollBarEnabled = false
                            scrollTo(0, 0)
                            setOnScrollChangeListener { v, scrollX, scrollY, _, _ ->
                                if (scrollX != 0 || scrollY != 0) {
                                    v.scrollTo(0, 0)
                                }
                            }

                            settings.apply {
                                javaScriptEnabled = true
                                domStorageEnabled = true
                                databaseEnabled = true
                                mediaPlaybackRequiresUserGesture = false
                                cacheMode = WebSettings.LOAD_DEFAULT
                                useWideViewPort = true
                                loadWithOverviewMode = true
                            }
                            webChromeClient = WebChromeClient()
                            webViewClient = object : WebViewClient() {
                                override fun onPageFinished(view: WebView?, url: String?) {
                                    super.onPageFinished(view, url)
                                    view?.evaluateJavascript(arcadeScript, null)

                                    // Poller to start game and dismiss loading curtain
                                    var attempts = 0
                                    val handler = android.os.Handler(android.os.Looper.getMainLooper())
                                    val runnable = object : Runnable {
                                        override fun run() {
                                            attempts++
                                            view?.evaluateJavascript("window.__av_boot ? window.__av_boot() : false;") { res ->
                                                if (res == "true") {
                                                    isGameReady = true
                                                    view.evaluateJavascript(
                                                        "var c = document.getElementById('canvas'); if (c) { c.style.transform = 'none'; c.style.top = '0px'; c.style.marginTop = '0px'; }",
                                                        null
                                                    )
                                                } else if (attempts < 40) {
                                                    handler.postDelayed(this, 500)
                                                }
                                            }
                                        }
                                    }
                                    handler.postDelayed(runnable, 600)
                                }
                            }
                            loadUrl("https://archive.org/embed/$identifier")
                            webViewRef = this
                            inputHandler.bindWebView(this)
                        }
                    },
                    modifier = Modifier.fillMaxSize()
                )
            }

            // Dedicated Bottom Virtual Gamepad / Thumb Mouse Dock (in portrait mode)
            if (!isLandscape && isGamepadVisible) {
                VirtualGamepadDock(
                    inputHandler = inputHandler,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        // Native Retro Arcade Boot Screen Curtain (Zero Power Button Screen!)
        AnimatedVisibility(
            visible = !isGameReady,
            enter = fadeIn(),
            exit = fadeOut()
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0xFF090D14)),
                contentAlignment = Alignment.Center
            ) {
                Surface(
                    color = Color(0xFF131926),
                    shape = RoundedCornerShape(16.dp),
                    tonalElevation = 8.dp,
                    shadowElevation = 12.dp,
                    modifier = Modifier
                        .padding(24.dp)
                        .fillMaxWidth(if (isLandscape) 0.5f else 0.85f)
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Surface(
                            color = VaultSecondary.copy(alpha = 0.2f),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.SportsEsports,
                                contentDescription = null,
                                tint = VaultSecondary,
                                modifier = Modifier
                                    .padding(12.dp)
                                    .size(36.dp)
                            )
                        }

                        Text(
                            text = title,
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            maxLines = 2
                        )

                        Text(
                            text = "⚡ Launching em-dosbox retro system...",
                            color = VaultPrimary,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )

                        LinearProgressIndicator(
                            color = VaultSecondary,
                            trackColor = Color(0xFF263248),
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(4.dp)
                        )
                    }
                }
            }
        }
    }
}
