import { Link } from 'react-router-dom';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-gray-900">GPSA Graduate Student</h1>
          <h2 className="text-3xl font-bold text-blue-600">Symposium 2026</h2>
          <p className="text-sm text-gray-500 mt-3">University of Idaho</p>
        </div>

        <div className="space-y-4">
          <Link
            to="/judge"
            className="block w-full bg-blue-600 text-white py-4 rounded-xl text-lg font-medium hover:bg-blue-700 transition-colors shadow-sm"
          >
            Judge Scoring Portal
            <span className="block text-sm font-normal text-blue-200 mt-0.5">
              Enter your access code to score presentations
            </span>
          </Link>

          <Link
            to="/admin/login"
            className="block w-full bg-white text-gray-700 py-4 rounded-xl text-lg font-medium hover:bg-gray-50 transition-colors border border-gray-200 shadow-sm"
          >
            Admin Dashboard
            <span className="block text-sm font-normal text-gray-400 mt-0.5">
              Manage judges, projects, and results
            </span>
          </Link>
        </div>

        <p className="text-xs text-gray-400 mt-10">
          March 13, 2026 — Bruce Pitman Center — International Ballroom
        </p>
      </div>
    </div>
  );
}
