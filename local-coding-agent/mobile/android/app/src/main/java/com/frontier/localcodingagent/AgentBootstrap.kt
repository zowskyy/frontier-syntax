package com.frontier.localcodingagent

import android.content.Context
import org.json.JSONObject
import java.io.BufferedReader

data class AgentBootstrap(
    val version: String,
    val inferencePath: String,
    val checklist: List<String>,
    val resourceSummary: String,
    val termuxCommand: String,
) {
    companion object {
        fun load(context: Context): AgentBootstrap {
            val profile = readAsset(context, "mobile_profile.json")
            val script = readAsset(context, "termux_bootstrap.sh").trim()
            val json = JSONObject(profile)
            val checklist = json.getJSONArray("checklist").let { array ->
                (0 until array.length()).map { array.getString(it) }
            }
            return AgentBootstrap(
                version = json.getString("version"),
                inferencePath = json.getString("inference_path"),
                checklist = checklist,
                resourceSummary = json.getString("resource_summary"),
                termuxCommand = script,
            )
        }

        private fun readAsset(context: Context, name: String): String {
            return context.assets.open(name).bufferedReader().use(BufferedReader::readText)
        }
    }
}
