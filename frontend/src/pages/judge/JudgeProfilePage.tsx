import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../components/auth/useAuth';
import type { JudgeProfile } from '../../types';
import { actionClass, fieldClass } from '../../utils/competitionUi';

export function JudgeProfilePage() {
  const navigate = useNavigate();
  const { updateUser } = useAuth();
  const [profile, setProfile] = useState<JudgeProfile | null>(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    setError('');
    setLoading(true);
    try {
      const data = await apiFetch<JudgeProfile>('/judge/me');
      setProfile(data);
      setFirstName(data.First_Name);
      setLastName(data.Last_Name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load your name.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  if (loading) return <p role="status">Loading your judge profile…</p>;
  return (
    <section className="mx-auto max-w-xl py-2">
      <h2 className="text-2xl font-semibold text-gray-900">
        {profile?.Name_Confirmed_At ? 'Your judge name' : 'Confirm your name'}
      </h2>
      <p className="mt-3 text-base leading-7 text-gray-700">
        Use the name organizers should see beside your assignments and reviews.
        Your access code is personal to you. Anyone using it shares the same
        judge identity and saved work.
      </p>
      {error && <p role="alert" className="mt-4 rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">{error}</p>}
      {!profile ? (
        <button className={`${actionClass} mt-4`} onClick={() => void load()}>Retry loading your name</button>
      ) : (
        <form className="mt-6" onSubmit={async (event) => {
          event.preventDefault();
          setSaving(true);
          setError('');
          try {
            const saved = await apiFetch<JudgeProfile>('/judge/me', {
              method: 'PATCH',
              body: JSON.stringify({ First_Name: firstName.trim(), Last_Name: lastName.trim() }),
            });
            updateUser({ id: saved.Judge_ID, name: `${saved.First_Name} ${saved.Last_Name}` });
            navigate('/judge/projects', { state: { nameConfirmed: true } });
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Unable to save your name.');
          } finally {
            setSaving(false);
          }
        }}>
          <fieldset disabled={saving} className="grid gap-5 sm:grid-cols-2">
            <label className="text-sm font-semibold text-gray-900">
              First name
              <input required maxLength={100} autoComplete="given-name" className={fieldClass} value={firstName} onChange={event => setFirstName(event.target.value)} />
            </label>
            <label className="text-sm font-semibold text-gray-900">
              Last name
              <input required maxLength={100} autoComplete="family-name" className={fieldClass} value={lastName} onChange={event => setLastName(event.target.value)} />
            </label>
          </fieldset>
          <p className="mt-4 text-sm leading-6 text-gray-600">
            Changing your name asks organizers to recheck mentor conflicts. Your
            code, assignments, scores and recorded conflicts stay attached to you.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <button className={actionClass} disabled={saving || !firstName.trim() || !lastName.trim()}>
              {saving ? 'Saving your name…' : 'Confirm name and continue'}
            </button>
            {profile.Name_Confirmed_At && <Link className="inline-flex min-h-11 items-center text-sm font-semibold underline" to="/judge/projects">Cancel</Link>}
          </div>
        </form>
      )}
    </section>
  );
}
