package com.smarted.tv.ui.player

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.view.KeyEvent
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import org.json.JSONObject

/**
 * Player de vídeo/áudio (Media3/ExoPlayer).
 *
 * Suporta, com o tipo correto (ver [MediaSourceSpec]):
 *  - HLS (.m3u8), DASH (.mpd), progressive (MP4/MKV/WebM/TS…), áudio;
 *  - mídia local do SAF (`content://`) e `file://`;
 *  - cabeçalhos HTTP exigidos pela fonte (Referer/User-Agent/Authorization).
 *
 * Limites declarados na tela (nunca mascarados): DRM protegido por licença
 * externa, codec sem suporte no aparelho e protocolo desconhecido. O app NÃO
 * contorna DRM.
 *
 * Segurança: a URL completa e os cabeçalhos podem conter credenciais — por isso
 * nada disso é escrito no log (ver [redacted]).
 */
class PlayerActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        val url = intent.getStringExtra(EXTRA_STREAM_URL).orEmpty()
        val title = intent.getStringExtra(EXTRA_TITLE) ?: "Reprodução"
        val mime = intent.getStringExtra(EXTRA_MIME)
        val headers = readHeaders(intent.getStringExtra(EXTRA_HEADERS))
        val subtitles = intent.getStringArrayListExtra(EXTRA_SUBTITLES).orEmpty()
        val isLive = intent.getBooleanExtra(EXTRA_IS_LIVE, false)

        val spec = MediaSourceSpec(
            uri = url,
            mimeHint = mime,
            headers = headers,
            title = title,
            isLive = isLive,
            subtitles = subtitles,
        )

        setContent {
            Box(Modifier.fillMaxSize().background(Color.Black)) {
                when {
                    url.isBlank() -> Message("Nenhum endereço de mídia foi informado")
                    !spec.isSupported -> Message(
                        "Protocolo \"${spec.scheme}\" não é suportado pelo player.\n" +
                            "Este app reproduz http(s), content:// (SAF) e arquivos locais."
                    )
                    else -> VideoPlayer(spec)
                }
                Text(
                    title,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    modifier = Modifier.align(Alignment.TopStart).padding(24.dp),
                )
            }
        }
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        when (keyCode) {
            KeyEvent.KEYCODE_BACK, KeyEvent.KEYCODE_ESCAPE -> {
                finish()
                return true
            }
        }
        return super.onKeyDown(keyCode, event)
    }

    @Composable
    private fun Message(text: String) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text(text, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Medium)
        }
    }

    @Composable
    private fun VideoPlayer(spec: MediaSourceSpec) {
        val context = LocalContext.current
        var error by remember { mutableStateOf<String?>(null) }

        val player = remember(spec) {
            ExoPlayer.Builder(context).build().apply {
                // `MediaSource` explícito: HLS/DASH sem extensão só funcionam assim
                setMediaSource(MediaSourceSpec.buildSource(context, spec))
                prepare()
                playWhenReady = true
            }
        }

        DisposableEffect(player) {
            val listener = object : Player.Listener {
                override fun onPlayerError(e: PlaybackException) {
                    error = describePlaybackError(e)
                }
            }
            player.addListener(listener)
            onDispose {
                player.removeListener(listener)
                player.release()
            }
        }

        Box(Modifier.fillMaxSize()) {
            AndroidView(
                factory = { ctx ->
                    PlayerView(ctx).apply {
                        this.player = player
                        useController = true
                        setShowBuffering(PlayerView.SHOW_BUFFERING_ALWAYS)
                    }
                },
                modifier = Modifier.fillMaxSize(),
            )
            error?.let { msg ->
                Column(
                    Modifier.align(Alignment.BottomCenter).padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text("Não foi possível reproduzir", color = Color.White,
                        fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Text(msg, color = Color(0xFFFFB4A9), fontSize = 13.sp)
                }
            }
        }
    }

    /** Traduz o erro do ExoPlayer para linguagem honesta, sem vazar credenciais. */
    private fun describePlaybackError(e: PlaybackException): String = when (e.errorCode) {
        PlaybackException.ERROR_CODE_IO_BAD_HTTP_STATUS ->
            "O servidor respondeu ${httpStatus(e)}. Verifique se o link exige login ou expirou."
        PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_FAILED ->
            "Não foi possível conectar ao servidor."
        PlaybackException.ERROR_CODE_IO_NETWORK_CONNECTION_TIMEOUT ->
            "Tempo de conexão esgotado."
        PlaybackException.ERROR_CODE_PARSING_CONTAINER_MALFORMED,
        PlaybackException.ERROR_CODE_PARSING_MANIFEST_MALFORMED ->
            "O manifesto/formato está corrompido ou não é o tipo indicado."
        PlaybackException.ERROR_CODE_PARSING_MANIFEST_UNSUPPORTED ->
            "Manifesto não suportado pelo player."
        PlaybackException.ERROR_CODE_DECODER_INIT_FAILED,
        PlaybackException.ERROR_CODE_DECODING_FAILED ->
            "O aparelho não suporta o codec deste arquivo."
        PlaybackException.ERROR_CODE_DRM_LICENSE_ACQUISITION_FAILED,
        PlaybackException.ERROR_CODE_DRM_LICENSE_EXPIRED,
        PlaybackException.ERROR_CODE_DRM_UNSPECIFIED ->
            "Conteúdo protegido por DRM: este app não reproduz DRM nem contorna proteção."
        else -> "Falha de reprodução (${e.errorCodeName})."
    }

    private fun httpStatus(e: PlaybackException): String =
        e.cause?.message?.let { msg -> Regex("\\b(4\\d{2}|5\\d{2})\\b").find(msg)?.value }.orEmpty()
            .ifBlank { "erro" }

    companion object {
        private const val EXTRA_STREAM_URL = "stream_url"
        private const val EXTRA_TITLE = "title"
        private const val EXTRA_MIME = "mime"
        private const val EXTRA_HEADERS = "headers"
        private const val EXTRA_SUBTITLES = "subtitles"
        private const val EXTRA_IS_LIVE = "is_live"

        /**
         * @param mimeHint HLS/DASH quando a URI não tem extensão
         * @param headers cabeçalhos HTTP necessários (não são logados)
         */
        fun intent(
            context: Context,
            streamUrl: String,
            title: String,
            mimeHint: String? = null,
            headers: Map<String, String> = emptyMap(),
            subtitles: List<String> = emptyList(),
            isLive: Boolean = false,
        ): Intent = Intent(context, PlayerActivity::class.java)
            .putExtra(EXTRA_STREAM_URL, streamUrl)
            .putExtra(EXTRA_TITLE, title)
            .putExtra(EXTRA_MIME, mimeHint)
            .putExtra(EXTRA_HEADERS, encodeHeaders(headers))
            .putStringArrayListExtra(EXTRA_SUBTITLES, ArrayList(subtitles))
            .putExtra(EXTRA_IS_LIVE, isLive)

        fun intent(context: Context, spec: MediaSourceSpec): Intent =
            intent(context, spec.uri, spec.title, spec.mimeHint, spec.headers, spec.subtitles, spec.isLive)

        private fun encodeHeaders(headers: Map<String, String>): String? {
            if (headers.isEmpty()) return null
            val json = JSONObject()
            headers.forEach { (k, v) -> json.put(k, v) }
            return json.toString()
        }

        private fun readHeaders(raw: String?): Map<String, String> {
            if (raw.isNullOrBlank()) return emptyMap()
            return runCatching {
                val json = JSONObject(raw)
                json.keys().asSequence().associateWith { json.optString(it) }
            }.getOrDefault(emptyMap())
        }
    }
}
