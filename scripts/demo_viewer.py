from pathlib import Path

import plotly.graph_objects as go

from jellyscope.config import JellyscopeConfig
from jellyscope.data.data_store import DataStore
from jellyscope.visualization.image_viewer import build_viewer_figure

config = JellyscopeConfig(data_dir=Path("data"))
store = DataStore.get(config)
dc = store.get_datacube("nircam")

fig_dict = build_viewer_figure(dc, channel_index=0, clumps=store.clumps, selected_ids=[0, 1])
fig1 = go.Figure(fig_dict)
fig1.show()
