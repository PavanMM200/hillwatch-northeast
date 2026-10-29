from pathlib import Path
import os,sys
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0,str(ROOT/'backend'))
