#!/usr/bin/env python

from rich import print
import click
import sh
import datetime
import plotext as plt

import time

class AMDUProfMonitor:

    profile_start = 'Profile Time: '

    state_init = 0,
    state_header_0 = 1
    state_header_1 = 2
    state_body = 3

    def __init__(self):
        self.state = self.state_init
        self.metrics = []
        self.data = None

    def __call__(self, line):
        line = line.strip()
        if self.state == self.state_init:
            if line.startswith(self.profile_start):
                self.start_time = datetime.datetime.strptime(line[len(self.profile_start):-1], "%Y/%m/%d %H:%M:%S:%f")
                self.state = self.state_header_0

        elif self.state == self.state_header_0:
            self.state = self.state_header_1
            groups = line.split(',')
            # self.groups = groups

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

            print(self.metric_names)

        elif self.state == self.state_body:
            vals = line.split(',')
            for i,v in enumerate(vals):
                self.metric_data[i].append(v)

            # self.plot('Total Mem Bw (GB/s)')
            groups = ('System', 'Package-0', 'Package-1')
            names = ('L3 Access', 'L3 Miss', 'L3 Miss %',)

            self.plot(groups, names)

        else:
            print(line)


    def plot(self, groups, names):
        
        vals = [[float(self.metric_data[self.metric_names.index((g,n))][-1]) for g in groups] for n in names]

        plt.simple_multiple_bar(groups, vals, width = 100, labels=names)
        plt.show()


@click.command()
def main():
    print("Hello")
    
    m = AMDUProfMonitor()

    pcm = sh.Command("/opt/AMDuProf_4.1-424/bin/AMDuProfPcm")
    pcm_args = ['-X', '-mmemory,ipc,l1,l2,l3', '-a', '-A', 'system,package', '-d3600']

    p = pcm(*pcm_args,
        _out=m,
        _bg=True,
        # _bg_exc=False,
        # _new_session=True
    )

    # time.sleep(10)

    p.wait()

    print("Done")


if __name__ == '__main__':
    main()