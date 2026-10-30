import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import type { Voter, VotingRound } from '../../types/competition';
import { actionClass, fieldClass, sectionClass } from '../../utils/competitionUi';
interface Talk { Candidate_ID: string; Round_ID: string; Presenter_Display_Name: string; Institution: string | null; Project_Title: string; Is_Active: boolean }
export function TalkCandidates({ round, onSaved }: { round: VotingRound; onSaved: () => void }) {
  const [talks, setTalks] = useState<Talk[]>([]);
  const [name, setName] = useState('');
  const [institution, setInstitution] = useState('');
  const [title, setTitle] = useState('');
  const [editing, setEditing] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const endpoint = `/voting/admin/rounds/${round.Round_ID}/talks`;
  useEffect(() => { apiFetch<Talk[]>(endpoint).then(setTalks).catch(e => setError(e.message)); }, [endpoint]);
  async function write(body: Omit<Talk, 'Candidate_ID' | 'Round_ID'>, id = '') {
    setBusy(true); setError('');
    try {
      await apiFetch(`${endpoint}${id ? `/${id}` : ''}`, { method: id ? 'PUT' : 'POST', body: JSON.stringify(body) });
      setTalks(await apiFetch<Talk[]>(endpoint)); setName(''); setInstitution(''); setTitle(''); setEditing(''); onSaved();
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to save speaker'); }
    finally { setBusy(false); }
  }
  return <section className={sectionClass}><h2 className="text-xl font-semibold">Talk candidates</h2>
    {error && <p role="alert">{error}</p>}
    <ul className="divide-y divide-gray-300">{talks.map(t => <li className="py-3" key={t.Candidate_ID}><p className="font-semibold">{t.Presenter_Display_Name}{!t.Is_Active && ' (withdrawn)'}</p><p>{t.Institution} {t.Project_Title}</p><div className="flex flex-wrap gap-3 mt-2">{round.Status === 'draft' && <button className={actionClass} disabled={busy} onClick={() => { setEditing(t.Candidate_ID); setName(t.Presenter_Display_Name); setInstitution(t.Institution || ''); setTitle(t.Project_Title); }}>Edit speaker</button>}<button className={actionClass} disabled={busy} onClick={() => write({ ...t, Is_Active: !t.Is_Active }, t.Candidate_ID)}>{t.Is_Active ? 'Withdraw' : 'Reinstate'}</button></div></li>)}</ul>
    {round.Status === 'draft' && <form className="mt-4 grid gap-3" onSubmit={e => { e.preventDefault(); write({ Presenter_Display_Name: name, Institution: institution || null, Project_Title: title, Is_Active: true }, editing); }}>
      <label>Speaker name<input className={fieldClass} required maxLength={300} value={name} onChange={e => setName(e.target.value)} /></label>
      <label>Institution (optional)<input className={fieldClass} maxLength={200} value={institution} onChange={e => setInstitution(e.target.value)} /></label>
      <label>Talk title (optional)<input className={fieldClass} maxLength={500} value={title} onChange={e => setTitle(e.target.value)} /></label>
      <button className={actionClass} disabled={busy}>{editing ? 'Save speaker' : 'Add speaker'}</button>
      {editing && <button type="button" className={actionClass} onClick={() => { setEditing(''); setName(''); setTitle(''); setInstitution(''); }}>Cancel edit</button>}
    </form>}
  </section>;
}
export function TalkVoterAccess({ voter, rounds, onSaved }: { voter: Voter; rounds: VotingRound[]; onSaved: () => void }) {
  const [talks, setTalks] = useState<Talk[]>([]);
  const [trainee, setTrainee] = useState(voter.Is_Trainee);
  const [confirmed, setConfirmed] = useState(voter.Talk_Affiliation_Confirmed);
  const [ids, setIds] = useState(voter.Presenter_Talk_IDs);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const roundKeys = rounds.filter(r => r.Candidate_Type === 'talk').map(r => r.Round_ID).sort().join(',');
  useEffect(() => {
    Promise.all(roundKeys.split(',').filter(Boolean).map(id => apiFetch<Talk[]>(`/voting/admin/rounds/${id}/talks`))).then(lists => setTalks(lists.flat())).catch(e => setError(e.message));
  }, [roundKeys]);
  return <details className="mt-3"><summary className="min-h-11 py-3 cursor-pointer font-semibold">Talk voting access</summary><p>Staff must confirm trainee status and all talks this attendee presents. Leave talks unselected for a non-speaker.</p>
    <label className="flex min-h-11 gap-3 items-center"><input type="checkbox" checked={trainee} onChange={e => setTrainee(e.target.checked)} />Organizer-approved trainee</label>
    {talks.map(t => <label className="flex min-h-11 gap-3 items-center" key={t.Candidate_ID}><input type="checkbox" checked={ids.includes(t.Candidate_ID)} onChange={e => setIds(e.target.checked ? [...ids, t.Candidate_ID] : ids.filter(id => id !== t.Candidate_ID))} />{t.Presenter_Display_Name} ({rounds.find(r => r.Round_ID === t.Round_ID)?.Round_Name})</label>)}
    <label className="flex min-h-11 gap-3 items-center"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />Talk affiliations confirmed by registration staff</label>
    <button className={actionClass} disabled={busy} onClick={async () => { setBusy(true); setError(''); try { await apiFetch(`/voting/admin/voters/${voter.Voter_ID}/talk-access`, { method: 'PUT', body: JSON.stringify({ Is_Trainee: trainee, Talk_Affiliation_Confirmed: confirmed, Presenter_Talk_IDs: ids }) }); onSaved(); } catch (e) { setError(e instanceof Error ? e.message : 'Unable to save access'); } finally { setBusy(false); } }}>Save talk access</button>
    {error && <p role="alert">{error}</p>}
  </details>;
}
