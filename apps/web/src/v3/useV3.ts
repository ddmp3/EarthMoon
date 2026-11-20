import { useEffect, useMemo, useState } from 'react'
import { v3, type CellProps, type Coverage, type MethodSource, type Scenario, type Status, type Zone } from './api'

export interface SiteV3 {
  id: string
  cell: string | null
  values: Record<string, CellProps> | null
  reason?: string
}

export interface V3Release {
  release: string
  run: string
  protocol?: string
  commit?: string
  grid: { tau: number[]; min_cells: number[]; nominal: { tau: number; min_cells: number } }
  geology?: unknown
}

/** What a v2 mission needs from the current v3 release. Every part loads on its own: a missing part never blocks
 *  the v2 page, it is just not shown. `scenarioId` null means the mission has no v3 scenario (yet). */
export function useV3(scenarioId: string | null) {
  const [release, setRelease] = useState<V3Release | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [status, setStatus] = useState<Status | null>(null)
  const [method, setMethod] = useState<{ sources: MethodSource[]; processing: Record<string, unknown>[] } | null>(null)
  const [unavailable, setUnavailable] = useState<string | null>(null)
  const [envChoice, setEnv] = useState('')
  const [tauChoice, setTau] = useState<number | null>(null)
  const [minChoice, setMin] = useState<number | null>(null)
  const [coverageAt, setCoverage] = useState<{ key: string; coverage: Coverage['coverage'] | null } | null>(null)
  const [zonesAt, setZones] = useState<{ key: string; total: number; zones: Zone[] } | null>(null)
  const [sitesAt, setSites] = useState<{ key: string; sites: Record<string, SiteV3> } | null>(null)

  useEffect(() => {
    let alive = true
    v3.releases()
      .then(async (idx) => {
        const [rel, sc, st, me] = await Promise.all([v3.release(idx.current), v3.scenarios(), v3.status(), v3.method()])
        if (!alive) return
        const info = idx.releases.find((r) => r.id === idx.current)
        setRelease({ ...rel, protocol: info?.protocol, commit: info?.commit })
        setScenarios(sc.scenarios)
        setStatus(st)
        setMethod(me)
      })
      .catch((e: unknown) => alive && setUnavailable(e instanceof Error ? e.message : String(e)))
    return () => {
      alive = false
    }
  }, [])

  const scenario = useMemo(() => scenarios.find((s) => s.id === scenarioId) ?? null, [scenarios, scenarioId])
  const env = scenario?.assessed_targets.includes(envChoice) ? envChoice : (scenario?.assessed_targets[0] ?? '')
  const tau = tauChoice ?? release?.grid.nominal.tau ?? 0.5
  const minCells = minChoice ?? release?.grid.nominal.min_cells ?? 3
  const covKey = `${scenario?.id}|${env}`
  const zonesKey = `${covKey}|${tau}|${minCells}`

  useEffect(() => {
    if (!scenario || !env) return
    let alive = true
    v3.coverage(scenario.id, env)
      .then((c) => alive && setCoverage({ key: covKey, coverage: c.coverage }))
      .catch(() => alive && setCoverage({ key: covKey, coverage: null }))
    return () => {
      alive = false
    }
  }, [scenario, env, covKey])

  useEffect(() => {
    if (!scenario || !env) return
    let alive = true
    v3.zones(scenario.id, env, tau, minCells, 50)
      .then((p) => alive && setZones({ key: zonesKey, total: p.total, zones: p.zones }))
      .catch(() => alive && setZones({ key: zonesKey, total: 0, zones: [] }))
    return () => {
      alive = false
    }
  }, [scenario, env, tau, minCells, zonesKey])

  useEffect(() => {
    if (!scenario) return
    let alive = true
    v3.sites(scenario.id)
      .then((r) => alive && setSites({ key: scenario.id, sites: Object.fromEntries(r.points.map((p) => [p.id, p])) }))
      .catch(() => alive && setSites({ key: scenario.id, sites: {} }))
    return () => {
      alive = false
    }
  }, [scenario])

  // dimensions the release carries: topography always, geology once T46 is in it
  const available = release?.geology ? ['topography', 'geology'] : ['topography']
  return {
    release, scenarios, scenario, status, method, unavailable, available,
    env, setEnv, tau, setTau, minCells, setMin,
    coverage: coverageAt?.key === covKey ? coverageAt.coverage : null,
    zones: zonesAt?.key === zonesKey ? zonesAt : null,
    zonesKey,
    sites: sitesAt && sitesAt.key === scenario?.id ? sitesAt.sites : null,
  }
}

export type V3State = ReturnType<typeof useV3>
