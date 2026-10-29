"""Child process for cancellable MATLAB Engine execution. Never accept web commands."""
import sys
from pathlib import Path
from .config import ROOT

if __name__=='__main__':
    import matlab.engine
    engine=matlab.engine.start_matlab()
    try:
        engine.addpath(str(ROOT/'matlab'),nargout=0)
        engine.run_route_analysis(str(Path(sys.argv[1]).resolve()),nargout=0)
    finally: engine.quit()
