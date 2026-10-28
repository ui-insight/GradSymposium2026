import type { AttendeeChoiceEntry, AttendeeChoiceReport as Report } from '../../types/competition';
import { actionClass } from '../../utils/competitionUi';

function ReportTable({ rows, caption }: { rows: AttendeeChoiceEntry[]; caption: string }) {
  return <table className="mt-4 w-full table-fixed text-left text-sm">
    <caption className="sr-only">{caption}</caption>
    <thead><tr>
      <th scope="col" className="w-14 border-b border-gray-300 py-3 pr-2">Rank</th>
      <th scope="col" className="w-20 border-b border-gray-300 py-3 pr-2">Poster</th>
      <th scope="col" className="border-b border-gray-300 py-3 pr-2">Presentation</th>
      <th scope="col" className="w-14 border-b border-gray-300 py-3 text-right">Votes</th>
    </tr></thead>
    <tbody>{rows.map(row => <tr key={row.Project_Number}>
      <td className="border-b border-gray-200 py-4 pr-2 align-top">{row.Vote_Rank}{row.Tied_Count > 1 && <span className="block text-gray-600">(tie)</span>}</td>
      <th scope="row" className="break-words border-b border-gray-200 py-4 pr-2 align-top font-mono font-semibold">{row.Project_Number}</th>
      <td className="break-words border-b border-gray-200 py-4 pr-2 align-top"><p className="font-semibold">{row.Presenter_Display_Name}</p><p className="mt-1 leading-6 text-gray-600">{row.Project_Title}</p></td>
      <td className="border-b border-gray-200 py-4 text-right align-top font-semibold tabular-nums">{row.Votes}</td>
    </tr>)}</tbody>
  </table>;
}

export function AttendeeChoiceReport({ report, busy, download }: {
  report: Report; busy: boolean; download: () => void;
}) {
  return <section className="mt-8 border-t border-gray-300 pt-6" aria-labelledby="attendee-report-heading">
    <h3 id="attendee-report-heading" className="text-xl font-semibold">Attendee choice: top 10 by votes</h3>
    <p className="mt-3 max-w-[70ch] text-sm leading-6">Unweighted attendee vote counts, separate from rubric judging scores. Equal counts share a vote rank. Poster-number ordering does not break ties or select award winners.</p>
    {report.Eligible_Count === 0 ? <p className="mt-4 text-sm">No active, eligible posters are available for this round’s report.</p> : <>
      <p className="mt-4 text-sm font-semibold">Showing {report.Top_Ten.length} of {report.Eligible_Count} eligible posters, including any with zero votes.</p>
      {report.Cutoff_Spans_Ten && <p role="status" className="mt-4 border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950">A tie crosses the top-10 cutoff at {report.Cutoff_Votes} {report.Cutoff_Votes === 1 ? 'vote' : 'votes'}. {report.Additional_Cutoff_Ties.length} additional {report.Additional_Cutoff_Ties.length === 1 ? 'poster has' : 'posters have'} the same count and {report.Additional_Cutoff_Ties.length === 1 ? 'is' : 'are'} listed below. The cutoff is not an award decision.</p>}
      <ReportTable rows={report.Top_Ten} caption="First ten posters by unweighted attendee vote count; equal counts share rank" />
      {report.Additional_Cutoff_Ties.length > 0 && <div className="mt-6">
        <h4 className="text-lg font-semibold">Additional posters tied at the cutoff</h4>
        <ReportTable rows={report.Additional_Cutoff_Ties} caption="Posters beyond position ten with the same vote count as the cutoff" />
      </div>}
    </>}
    <button className={`${actionClass} mt-5`} disabled={busy} onClick={download}>Download attendee-choice report (CSV)</button>
    <p className="mt-2 text-sm text-gray-600">The report export includes the displayed top ten and any additional cutoff ties. The complete tally is available below.</p>
  </section>;
}
