package com.artflow.tablet.brush

class StrokeStabilizer(var streamline: Float = 0.5f) {

    private val pointHistory = mutableListOf<StrokePoint>()
    private var filteredPoint: StrokePoint? = null

    fun reset() {
        pointHistory.clear()
        filteredPoint = null
    }

    /**
     * Filters input point using exponential moving average according to streamline strength.
     * Higher streamline = smoother path, dampening high-frequency hand tremors.
     */
    fun processPoint(raw: StrokePoint): StrokePoint {
        if (streamline <= 0.01f) {
            pointHistory.add(raw)
            return raw
        }

        val prev = filteredPoint
        if (prev == null) {
            filteredPoint = raw
            pointHistory.add(raw)
            return raw
        }

        // Weight formula: higher streamline gives more weight to previous history
        val alpha = (1.0f - streamline.coerceIn(0f, 0.95f)).coerceIn(0.05f, 1.0f)
        val smoothed = prev.interpolate(raw, alpha)
        filteredPoint = smoothed
        pointHistory.add(smoothed)
        return smoothed
    }

    fun getInterpolatedPointsForLastSegment(stepDistance: Float): List<StrokePoint> {
        val size = pointHistory.size
        if (size < 2) return emptyList()

        val p1 = pointHistory[size - 2]
        val p2 = pointHistory[size - 1]
        val p0 = if (size >= 3) pointHistory[size - 3] else p1
        val p3 = p2

        return CatmullRomSpline.generateInterpolatedSegment(p0, p1, p2, p3, stepDistance)
    }

    fun getAllCommittedPoints(): List<StrokePoint> = pointHistory.toList()
}
