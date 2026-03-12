import { useState, useEffect, useRef } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { apiFetch } from '../../api/client';
import type { EventSummary, Event } from '../../types';

export function AdminDashboardPage() {
  const [summary, setSummary] = useState<EventSummary | null>(null);
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const qrRef = useRef<HTMLDivElement>(null);

  const appUrl = `${window.location.origin}/judge`;

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const ev = await apiFetch<Event | null>('/events/active');
      setEvent(ev);
      if (ev) {
        const s = await apiFetch<EventSummary>(`/results/summary?event_id=${ev.Event_ID}`);
        setSummary(s);
      }
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="text-gray-500">Loading...</div>;

  if (!event) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700">No active event</h2>
        <p className="text-gray-500 mt-2">Create an event to get started.</p>
      </div>
    );
  }

  const cards = summary ? [
    { label: 'Projects', value: summary.Total_Projects, sub: `${summary.Poster_Count} poster, ${summary.Art_Count} art` },
    { label: 'Judges', value: summary.Total_Judges, sub: 'registered' },
    { label: 'Scores Submitted', value: summary.Total_Scores_Submitted, sub: 'judge-project pairs' },
    { label: 'Coverage', value: `${summary.Scoring_Coverage_Percent}%`, sub: `${summary.Projects_With_Scores} of ${summary.Total_Projects} projects scored` },
  ] : [];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">{event.Event_Name}</h1>
        <p className="text-gray-500">
          {new Date(event.Event_Date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          {event.Location && ` — ${event.Location}`}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map(card => (
          <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-6">
            <p className="text-sm font-medium text-gray-500">{card.label}</p>
            <p className="text-3xl font-bold text-gray-900 mt-1">{card.value}</p>
            <p className="text-xs text-gray-400 mt-1">{card.sub}</p>
          </div>
        ))}
      </div>

      {/* Judge QR Code */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Judge Login QR Code</h2>
        <p className="text-sm text-gray-500 mb-4">
          Print or display this QR code for judges to scan and access the scoring app.
        </p>
        <div className="flex items-start gap-6">
          <div ref={qrRef} className="bg-white p-4 rounded-lg border border-gray-200 inline-block">
            <QRCodeSVG value={appUrl} size={180} level="M" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-gray-600 mb-1">Link:</p>
            <code className="text-sm bg-gray-100 px-3 py-1.5 rounded block mb-4 text-gray-800 break-all">
              {appUrl}
            </code>
            <button
              onClick={() => {
                const svg = qrRef.current?.querySelector('svg');
                if (!svg) return;
                const svgData = new XMLSerializer().serializeToString(svg);
                const blob = new Blob([svgData], { type: 'image/svg+xml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'gpsa-judge-qr.svg';
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Download QR Code
            </button>
          </div>
        </div>
      </div>

      <button
        onClick={loadData}
        className="text-sm text-blue-600 hover:text-blue-800"
      >
        Refresh
      </button>
    </div>
  );
}
