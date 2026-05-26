export default function PipelinePage() {
  const stages = [
    { name: 'Intent Extraction', status: 'completed', duration: '1.2s' },
    { name: 'CCL Generation', status: 'completed', duration: '2.8s' },
    { name: 'Knowledge Graph', status: 'completed', duration: '0.5s' },
    { name: 'Probe Execution', status: 'completed', duration: '0.3s' },
    { name: 'Validation', status: 'completed', duration: '0.2s' },
    { name: 'XAI Analysis', status: 'completed', duration: '0.1s' },
    { name: 'Report Generation', status: 'completed', duration: '0.1s' },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Pipeline Execution</h2>

      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <div className="space-y-4">
          {stages.map((stage, i) => (
            <div key={i} className="flex items-center space-x-4">
              <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center text-sm">
                ✓
              </div>
              <div className="flex-1">
                <p className="font-medium">{stage.name}</p>
                <p className="text-sm text-gray-400">{stage.duration}</p>
              </div>
              <span className="text-green-400 text-sm">{stage.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
