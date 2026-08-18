-- Nothing lost: modelled + quarantined must equal received.
select *
from {{ ref('dq_completeness') }}
where not reconciles
