import sys
sys.path.append('.')
sys.path.append('backend')
import app.config
from app.services.chart_service import build_alligator_figure
import traceback

try:
    print("Starting chart build...")
    fig = build_alligator_figure("PST.MI", 70)
    print("Figure built successfully:", fig)
except BaseException as e:
    print("CAUGHT EXCEPTION:", type(e), e)
    traceback.print_exc()
