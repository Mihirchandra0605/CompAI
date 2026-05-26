export default function ReportsPage() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Compliance Reports</h2>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold mb-4">TRAI QoS 2024 — §4.2.1 VoLTE Latency</h3>

        <div className="space-y-4">
          <div className="flex justify-between items-center p-3 bg-gray-700 rounded">
            <span>Average RTT Latency</span>
            <span className="text-green-400">✅ 145.6ms ≤ 150ms</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-gray-700 rounded">
            <span>P95 RTT Latency</span>
            <span className="text-red-400">❌ 223.6ms &gt; 200ms</span>
          </div>
        </div>

        <div className="mt-6 p-4 bg-red-900/30 border border-red-700 rounded">
          <p className="font-semibold text-red-300">Verdict: NON-COMPLIANT</p>
          <p className="text-sm text-gray-400 mt-1">
            1 of 2 constraints failed. P95 latency exceeds threshold by 23.6ms.
          </p>
        </div>
      </div>
    </div>
  )
}
