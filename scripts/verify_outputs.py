import bootstrap,argparse,json
from pathlib import Path
from app.matlab_adapter import validate_outputs
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('segment_directory');p.add_argument('segment_json');a=p.parse_args()
    directory=Path(a.segment_directory).resolve();manifest=json.loads((directory/'input.json').read_text());segment=json.loads(Path(a.segment_json).read_text())
    stats,features=validate_outputs(directory,segment,manifest)
    print(json.dumps({'validated':True,'statistics':stats,'candidate_count':len(features)},indent=2))
