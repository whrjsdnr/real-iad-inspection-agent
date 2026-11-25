"""Create a separate all-product reference report from stored CSV; no DB/model writes."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.cohort_performance import derive


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--latest', type=Path, default=Path('/home/geonug/MV/outputs/fusion_agent_validation_20261124_v1/final_performance/latest.json'))
    parser.add_argument('--manifest', type=Path, default=Path('/home/geonug/MV/outputs/agent_integration_20261123_v1/inference_cohort_120000/manifest.csv'))
    parser.add_argument('--output', type=Path, default=root/'reports/cohort_performance/latest.json')
    args = parser.parse_args()
    report = derive(Path(json.loads(args.latest.read_text())['report']), args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    temporary.replace(args.output)
    print(json.dumps({'report': str(args.output), 'scope': report['scope'], 'overall': report['overall']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
