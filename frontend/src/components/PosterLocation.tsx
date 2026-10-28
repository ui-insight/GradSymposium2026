export interface PosterLocationFields {
  Board_Label?: string | null;
  Poster_Session?: string | null;
  Poster_Session_Time?: string | null;
  Table_Number?: string | null;
}

export function PosterLocation({ poster }: { poster: PosterLocationFields }) {
  return <div className="mt-2 break-words text-sm leading-6">
    <p>{poster.Board_Label ? `Board ${poster.Board_Label}` : poster.Table_Number ? `Board / table: ${poster.Table_Number}` : 'Location to be assigned'}</p>
    {poster.Board_Label && poster.Table_Number && poster.Table_Number !== poster.Board_Label && <p>Location: {poster.Table_Number}</p>}
    {poster.Poster_Session && <p>{poster.Poster_Session}{poster.Poster_Session_Time && ` · ${poster.Poster_Session_Time}`}</p>}
    {poster.Board_Label && !poster.Poster_Session && <p>Session to be confirmed</p>}
  </div>;
}
