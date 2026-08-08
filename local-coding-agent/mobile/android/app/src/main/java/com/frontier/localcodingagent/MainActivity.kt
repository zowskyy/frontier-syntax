package com.frontier.localcodingagent

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.frontier.localcodingagent.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val bootstrap = AgentBootstrap.load(this)
        binding.titleText.text = getString(R.string.app_title)
        binding.versionText.text = getString(R.string.version_label, bootstrap.version)
        binding.profileText.text = bootstrap.inferencePath
        binding.checklistText.text = bootstrap.checklist.joinToString("\n") { "• $it" }
        binding.resourceText.text = bootstrap.resourceSummary
        binding.bootstrapText.text = bootstrap.termuxCommand

        binding.copyBootstrapButton.setOnClickListener {
            val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText("bootstrap", bootstrap.termuxCommand))
            Toast.makeText(this, R.string.copied_bootstrap, Toast.LENGTH_SHORT).show()
        }
    }
}
