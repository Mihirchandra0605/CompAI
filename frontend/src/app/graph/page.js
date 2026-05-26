export default function GraphPage() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Compliance Knowledge Graph</h2>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 text-center">
        <div className="py-16">
          <p className="text-gray-400 mb-4">Knowledge Graph Visualization</p>
          <p className="text-sm text-gray-500">
            Connected to NetworkX backend. Visualize the relationship between
            regulations, clauses, constraints, probes, and evidence.
          </p>
          <div className="mt-8 inline-block text-left font-mono text-sm text-gray-300">
            <pre>{`
  TRAI QoS 2024
    └─ Clause 4.2.1 [MANDATORY]
         └─ Intent: VoLTE Latency Quality
              └─ Objective (AND)
                   ├─ con:001 avg RTT ≤ 150ms → ✅ PASS
                   └─ con:002 p95 RTT ≤ 200ms → ❌ FAIL
            `}</pre>
          </div>
        </div>
      </div>
    </div>
  )
}
