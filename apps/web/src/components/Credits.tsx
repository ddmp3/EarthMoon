import { useT } from '../i18n'
import { pageCredits } from '../credits'
import type { Body, SelectedMode } from '../store'

export function Credits({ body, mode, env }: { body: Body; mode: SelectedMode | null; env: string | null }) {
  const { t } = useT()
  return (
    <div>
      <h3>{t.imagesTitle}</h3>
      <ul>
        {pageCredits(t, body, mode, env).map((c) => <li key={c}>{c}</li>)}
      </ul>
    </div>
  )
}
