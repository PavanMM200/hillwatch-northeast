from datetime import datetime, timezone, timedelta

def road_status(*, candidates, coverage_ok, observations, incidents=(), verified=(), stale_days=14, at=None):
    at=at or datetime.now(timezone.utc)
    fresh=bool(observations) and all(at-datetime.fromisoformat(t.replace('Z','+00:00')) <= timedelta(days=stale_days) for t in observations)
    closures=[v for v in verified if v.get('closure') and v.get('decision')=='VERIFIED' and datetime.fromisoformat(v['expires_at'])>at]
    reports=[i for i in incidents if i['kind']=='BLOCKAGE' and i['status']=='ACTIVE' and i['moderation']=='UNVERIFIED' and at-datetime.fromisoformat(i['observed_at'])<=timedelta(days=stale_days)]
    impact=any(c['properties']['potential_road_impact'] for c in candidates)
    if closures: status='CONFIRMED ROAD CLOSURE'
    elif reports: status='REPORTED BLOCKAGE — UNVERIFIED'
    elif not coverage_ok: status='LIMITED IMAGE COVERAGE'
    elif not fresh: status='HISTORICAL SURFACE-CHANGE ANALYSIS'
    elif impact: status='POSSIBLE LANDSLIDE WITH POTENTIAL ROAD IMPACT'
    elif candidates: status='LANDSLIDE CANDIDATE NEAR ROAD'
    else: status='NO SIGNIFICANT CHANGE DETECTED'
    return {'status':status,'landslide_candidates':len(candidates),'potential_road_impact':impact,
      'unverified_blockage_reports':len(reports),'official_closure':bool(closures),
      'evidence_fresh':fresh,'coverage_sufficient':coverage_ok,'official_evidence':closures,
      'conflicting_evidence':bool(closures and coverage_ok and not candidates),
      'limitation':'No detected change does not establish that the road is clear. Experimental imagery analysis cannot confirm physical blockage.'}
