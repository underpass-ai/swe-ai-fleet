import PlannerBoard from './components/PlannerBoard'
import ContextViewer from './components/ContextViewer'

export default function App() {
  return (
    <main className="max-w-7xl mx-auto p-6 space-y-6 text-gray-900">
      <header className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-3xl font-light tracking-tight">PO Planner</h1>
          <p className="text-sm text-gray-500 mt-1">
            Agile workflow powered by DDD, NATS & gRPC
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          <span className="px-3 py-1 bg-blue-50 text-blue-700 rounded-full">
            React
          </span>
          <span className="px-3 py-1 bg-green-50 text-green-700 rounded-full">
            Tailwind
          </span>
          <span className="px-3 py-1 bg-purple-50 text-purple-700 rounded-full">
            NATS
          </span>
        </div>
      </header>

      <section className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <PlannerBoard />
        </div>
        <div className="lg:col-span-1">
          <ContextViewer />
        </div>
      </section>
    </main>
  )
}



