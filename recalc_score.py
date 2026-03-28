#!/usr/bin/env python3
from pathlib import Path
from lxml import etree
from pipeline.quality.metrics import QualityMetricsCalculator
from pipeline.quality.judge import QualityJudge

cache = Path('tmp/crash_cache_v3')
pages = sorted(cache.glob('page_*'))
scores = []

print(f'{"Page":<6} {"MC":>8} {"Score":>8} Judgment')
print('-' * 40)

for page_dir in pages:
    pnum_str = page_dir.name.replace('page_', '')
    pnum = int(pnum_str)
    xml_path = page_dir / 'transform' / f'CRASH_COMPLEXION_p{pnum_str}_transformed.xml'
    if not xml_path.exists():
        continue
    tree = etree.parse(str(xml_path))
    m = QualityMetricsCalculator.calculate(tree)
    decision = QualityJudge.evaluate(m)
    print(f'p{pnum:03}   {m.measure_completeness:>8.3f} {decision.overall_score:>8.3f}  {decision.judgment}')
    scores.append(decision.overall_score)

avg = sum(scores) / len(scores) if scores else 0
print()
print(f'Old overall_score: 0.594 (FAIL)')
print(f'New overall_score: {avg:.3f}')
from pipeline.quality.judge import QualityJudge, QualityMetrics
# Fake judgment on avg
print(f'Improvement: +{avg - 0.594:.3f}')
