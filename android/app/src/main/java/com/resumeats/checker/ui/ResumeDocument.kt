package com.resumeats.checker.ui

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.IOException

data class PickedResume(val fileName: String, val bytes: ByteArray)

suspend fun readResumeDocument(context: Context, uri: Uri): PickedResume = withContext(Dispatchers.IO) {
    val mime = context.contentResolver.getType(uri)
    if (mime !in setOf(
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    ) {
        throw IOException("Choose a PDF or DOCX document.")
    }
    val name = context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
        ?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        }
        ?.takeIf { it.endsWith(".pdf", true) || it.endsWith(".docx", true) }
        ?: throw IOException("The selected document must have a .pdf or .docx filename.")

    val output = ByteArrayOutputStream()
    context.contentResolver.openInputStream(uri)?.use { input ->
        val buffer = ByteArray(16 * 1024)
        var total = 0
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            total += read
            if (total > 5 * 1024 * 1024) throw IOException("Resume file must not exceed 5 MB.")
            output.write(buffer, 0, read)
        }
    } ?: throw IOException("The selected document could not be opened.")
    if (output.size() == 0) throw IOException("The selected document is empty.")
    PickedResume(name, output.toByteArray())
}
