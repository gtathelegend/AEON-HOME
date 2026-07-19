package com.example.aeon.model

import org.json.JSONObject

/**
 * Mirrors HubState.snapshot() from the Python hub.
 *
 * The phone renders what the hub constructs and computes no state of its own,
 * which is why the phone and the PC dashboard can never disagree.
 */
data class DeviceState(
    val id: String,
    val label: String,
    val on: Boolean,
    val level: Double?,
    val levelText: String,
    val levelName: String,
    val unit: String,
    val rangeLo: Double,
    val rangeHi: Double,
    val source: String,
    val confidence: Double,
    val online: Boolean,
    // "act" / "ask" / "abstain", or "held" when automation is switched off and
    // the model reached a decision it was not permitted to act on. Without this
    // the phone would report `model` while nothing was moving.
    val gate: String,
) {
    companion object {
        fun from(o: JSONObject): DeviceState {
            val range = o.optJSONArray("range")
            return DeviceState(
                id = o.getString("id"),
                label = o.optString("label", o.getString("id")),
                on = o.optBoolean("on"),
                level = if (o.isNull("level")) null else o.optDouble("level"),
                levelText = o.optString("level_text", "--"),
                levelName = o.optString("level_name", "level"),
                unit = o.optString("unit", ""),
                rangeLo = range?.optDouble(0) ?: 0.0,
                rangeHi = range?.optDouble(1) ?: 100.0,
                source = o.optString("source", "idle"),
                confidence = o.optDouble("confidence", 0.0),
                online = o.optBoolean("online", true),
                gate = o.optString("gate", "act"),
            )
        }
    }
}

data class LearnedRow(val device: String, val label: String, val text: String)

data class HubSnapshot(
    val clock: String,
    val clockDay: String,
    val nodeOnline: Boolean,
    val modelVersion: Int,
    val tempC: Double,
    val occupied: Boolean,
    val cloudBytes: Long,
    val spooled: Int,
    val pcReachable: Boolean,
    val devices: List<DeviceState>,
    val learned: List<LearnedRow>,
) {
    companion object {
        fun from(o: JSONObject): HubSnapshot {
            val devices = mutableListOf<DeviceState>()
            o.optJSONArray("devices")?.let { arr ->
                for (i in 0 until arr.length()) devices += DeviceState.from(arr.getJSONObject(i))
            }
            val learned = mutableListOf<LearnedRow>()
            o.optJSONArray("learned_week")?.let { arr ->
                for (i in 0 until arr.length()) {
                    val r = arr.getJSONObject(i)
                    learned += LearnedRow(
                        device = r.optString("device"),
                        label = r.optString("label"),
                        text = r.optString("text"),
                    )
                }
            }
            val node = o.optJSONObject("node")
            val ambient = o.optJSONObject("ambient")
            val egress = o.optJSONObject("egress")
            val policy = o.optJSONObject("policy")
            return HubSnapshot(
                clock = o.optString("clock", "--:--"),
                clockDay = o.optString("clock_day", ""),
                nodeOnline = node?.optBoolean("online") ?: false,
                modelVersion = policy?.optInt("model_v") ?: 0,
                tempC = ambient?.optDouble("temp_c") ?: 0.0,
                occupied = ambient?.optBoolean("occupied") ?: false,
                cloudBytes = egress?.optLong("cloud_bytes") ?: 0L,
                spooled = egress?.optInt("spooled") ?: 0,
                pcReachable = node?.optBoolean("pc_reachable") ?: true,
                devices = devices,
                learned = learned,
            )
        }
    }
}
