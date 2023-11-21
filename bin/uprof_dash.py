#!/usr/bin/env python


from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import cycle
from json import loads
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.message import Message
from textual.reactive import var
from textual.widgets import Footer, Header
from typing_extensions import Final

from textual_plotext import PlotextPlot

###------------------------------

import sh

class AMDUProfMonitor:

    profile_start = 'Profile Time: '

    state_init = 0,
    state_header_0 = 1
    state_header_1 = 2
    state_body = 3

    def __init__(self, callback=None):
        self.state = self.state_init
        self.callback = callback

    def __call__(self, line):
        line = line.strip()
        if self.state == self.state_init:
            if line.startswith(self.profile_start):
                self.start_time = datetime.strptime(line[len(self.profile_start):-1], "%Y/%m/%d %H:%M:%S:%f")
                self.state = self.state_header_0

        elif self.state == self.state_header_0:
            self.state = self.state_header_1
            groups = line.split(',')

            metric_groups = []
            cur_group = None
            for i,l in enumerate(groups):
                if l:
                    cur_group = l.replace(' (Aggregated)','')
                metric_groups.append( cur_group )

            self.metric_groups = metric_groups
                
        elif self.state == self.state_header_1:
            self.state = self.state_body
            cols = line.split(',')
            self.metric_names = [ ((g,c) if c else ('','')) for g,c in zip(self.metric_groups, cols) ]
            self.metric_data = [[] for _ in cols]

        elif self.state == self.state_body:
            vals = line.split(',')
            for i,v in enumerate(vals):
                self.metric_data[i].append(v)

            if self.callback:
                self.callback(self.metric_names, self.metric_data)

        else:
            print(line)

###------------------------------

class UProfHist(PlotextPlot):
    """A widget for plotting weather data."""

    def __init__(
        self,
        title: str,
        *,
        name: str | None = None,
        id: str | None = None,  # pylint:disable=redefined-builtin
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        """Initialise the hist widget.

        Args:
            name: The name of the hist widget.
            id: The ID of the hist widget in the DOM.
            classes: The CSS classes of the hist widget.
            disabled: Whether the hist widget is disabled or not.
        """
        super().__init__(name=name, id=id, classes=classes, disabled=disabled)
        self._title = title
        self._unit = "Loading..."
        self._data: list[float] = []

    def on_mount(self) -> None:
        """Plot the data using Plotext."""
        # self.plt.date_form("Y-m-d H:M")
        self.plt.title(self._title)
        # self.plt.xlabel("Time")


    def replot(self) -> None:
        """Redraw the plot."""
        self.plt.clear_data()
        # self.plt.ylabel(self._unit)
        # self.plt.plot(self._time, self._data, marker=self.marker)
        self.plt.multiple_bar(
            self.plot_groups, 
            self.vals, 
            label = self.plot_vars
        )
        
        self.refresh(layout=True)

    def update(self, names, data, plot_groups, plot_vars) -> None:
        """Update the data for the weather plot.

        Args:
            data: The data from the weather API.
            values: The name of the values to plot.
        """
        self.plot_groups = plot_groups
        self.plot_vars = plot_vars

        self.vals = [[float(data[names.index((g,n))][-1]) for g in plot_groups] for n in plot_vars]

        self.replot()

class UProfDashboardApp(App[None]):

    CSS = """
    Grid {
        grid-size: 2;
    }

    Weather {
        padding: 1 2;
    }
    """

    TITLE = "AMD uPROF PCM"

    BINDINGS = [
        ("d", "app.toggle_dark", "Toggle light/dark mode"),
        ("m", "marker", "Cycle example markers"),
        ("q", "app.quit", "Quit the example"),
    ]

    MARKERS = {
        "dot": "Dot",
        "hd": "High Definition",
        "fhd": "Higher Definition",
        "braille": "Braille",
        "sd": "Standard Definition",
    }

    marker: var[str] = var("sd")
    """The marker used for each of the plots."""

    def __init__(self) -> None:
        """Initialise the application."""
        super().__init__()
        self._markers = cycle(self.MARKERS.keys())
    
    def compose(self) -> ComposeResult:
        """Compose the display of the example app."""
        yield Header()
        # yield UProfHist("L3 Cache", id="l3cache")
        with Grid():
            yield UProfHist("L3 Cache", id="l3_cache")
            yield UProfHist("L3 Cache Miss", id="l3_cache_miss")
            yield UProfHist("Mem Bw (GB/s)", id="mem_bw")
            yield UProfHist("Mem RdWe Bw (GB/s)", id="mem_rd_wr_bw")
        with Grid():
            yield UProfHist("Mem Rd Bw (by chan)", id="mem_rdbw_chan")
            yield UProfHist("Mem We Bw (by chan)", id="mem_wrbw_chan")
        yield Footer()

    def on_mount(self) -> None:
        """Start profiling"""
        self.gather_counters()

    @dataclass
    class CounterData(Message):
        """Message posted every time there is a counter update"""
        names : list[str]
        values : list[str]

    @work(thread=True, exclusive=True)
    def gather_counters(self) -> None:
        print("Hello")

        def post_counters(names, data):
            """Callback function to """
            self.post_message(
                self.CounterData(names, data)
            )

        m = AMDUProfMonitor(callback=post_counters)

        pcm = sh.Command("/opt/AMDuProf_4.1-424/bin/AMDuProfPcm")
        pcm_args = ['-X', '-mmemory,ipc,l1,l2,l3', '-a', '-A', 'system,package', '-d3600']

        p = pcm(*pcm_args,
            _out=m,
            _bg=True,
        )

        p.wait()

        print("Done")

    @on(CounterData)
    def update_plots(self, event: CounterData) -> None:
        """Update the plots with data received from the API.

        Args:
            event: The counter data reception event.
        """

        with self.batch_update():
            
            groups = ('System', 'Package-0', 'Package-1')
            names = ('L3 Access', 'L3 Miss',)

            self.query_one("#l3_cache", UProfHist).update(
                event.names, event.values, groups, names
            )

            groups = ('System', 'Package-0', 'Package-1')
            names = ('L3 Miss %',)
            self.query_one("#l3_cache_miss", UProfHist).update(
                event.names, event.values, groups, names
            )

            groups = ('System', 'Package-0', 'Package-1')
            names = ('Total Mem Bw (GB/s)',)

            self.query_one("#mem_bw", UProfHist).update(
                event.names, event.values, groups, names
            )

            groups = ('System', 'Package-0', 'Package-1')
            names = ('Total Mem RdBw (GB/s)','Total Mem WrBw (GB/s)',)

            self.query_one("#mem_rd_wr_bw", UProfHist).update(
                event.names, event.values, groups, names
            )
            groups = ('Package-0', 'Package-1')
            names = (
                'Mem Ch-A RdBw (GB/s)',
                'Mem Ch-B RdBw (GB/s)',
                'Mem Ch-C RdBw (GB/s)',
                'Mem Ch-D RdBw (GB/s)',
                'Mem Ch-E RdBw (GB/s)',
                'Mem Ch-F RdBw (GB/s)',
                'Mem Ch-G RdBw (GB/s)',
                'Mem Ch-H RdBw (GB/s)',
                )
            self.query_one("#mem_rdbw_chan", UProfHist).update(
                event.names, event.values, groups, names
            )
            groups = ('Package-0', 'Package-1')
            names = (
                'Mem Ch-A WrBw (GB/s)',
                'Mem Ch-B WrBw (GB/s)',
                'Mem Ch-C WrBw (GB/s)',
                'Mem Ch-D WrBw (GB/s)',
                'Mem Ch-E WrBw (GB/s)',
                'Mem Ch-F WrBw (GB/s)',
                'Mem Ch-G WrBw (GB/s)',
                'Mem Ch-H WrBw (GB/s)',
                )
            self.query_one("#mem_wrbw_chan", UProfHist).update(
                event.names, event.values, groups, names
            )
if __name__ == "__main__":
    UProfDashboardApp().run()
