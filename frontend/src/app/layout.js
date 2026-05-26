import './globals.css'

export const metadata = {
  title: 'CompliAI — Compliance Digital Twin',
  description: 'Autonomous Compliance Engineering for Telecom Systems',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-gray-900 text-gray-100 min-h-screen">
        <div className="flex">
          <aside className="w-64 bg-gray-800 min-h-screen p-4 border-r border-gray-700">
            <h1 className="text-xl font-bold text-blue-400 mb-8">CompliAI</h1>
            <nav className="space-y-2">
              <a href="/" className="block px-3 py-2 rounded hover:bg-gray-700 text-gray-300">
                Dashboard
              </a>
              <a href="/pipeline" className="block px-3 py-2 rounded hover:bg-gray-700 text-gray-300">
                Pipeline
              </a>
              <a href="/reports" className="block px-3 py-2 rounded hover:bg-gray-700 text-gray-300">
                Reports
              </a>
              <a href="/graph" className="block px-3 py-2 rounded hover:bg-gray-700 text-gray-300">
                Knowledge Graph
              </a>
            </nav>
          </aside>
          <main className="flex-1 p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
