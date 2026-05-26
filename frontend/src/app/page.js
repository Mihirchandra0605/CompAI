export default function Dashboard() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Compliance Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-sm text-gray-400 uppercase">Active Regulations</h3>
          <p className="text-3xl font-bold mt-2">1</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-sm text-gray-400 uppercase">Last Verdict</h3>
          <p className="text-3xl font-bold mt-2 text-red-400">NON-COMPLIANT</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h3 className="text-sm text-gray-400 uppercase">Confidence</h3>
          <p className="text-3xl font-bold mt-2 text-blue-400">97%</p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-semibold mb-4">Recent Compliance Runs</h3>
        <table className="w-full">
          <thead>
            <tr className="text-gray-400 text-sm border-b border-gray-700">
              <th className="text-left py-2">Regulation</th>
              <th className="text-left py-2">Verdict</th>
              <th className="text-left py-2">Confidence</th>
              <th className="text-left py-2">Date</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-gray-700">
              <td className="py-3">TRAI QoS 2024, §4.2.1</td>
              <td className="py-3"><span className="text-red-400">❌ NON-COMPLIANT</span></td>
              <td className="py-3">97%</td>
              <td className="py-3 text-gray-400">2024-11-15</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
