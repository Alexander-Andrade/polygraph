import serial
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import struct
import time
import datetime as dt
import random
import matplotlib.animation as animation
import sys

n_sampling_levels = 4096


class ComMediator:
    def __init__(self, com_name='COM3', com_speed=9600, **kwargs):
        #len(sync_seq) == len(data)
        self.n_sensors = kwargs.get('n_sensors',3)
        self.byteorder = kwargs.get('byteorder','little')
        self.data_size = kwargs.get('data_size',2)
        #value limits
        self.val_lim = kwargs.get('val_lim',(0,1024))
        self.sync_seq = int.to_bytes(kwargs.get('num_sync_seq',65535), self.data_size, byteorder=self.byteorder)
        self.n_sync_attempts = kwargs.get('n_sync_attempts',12)
        self.port = serial.Serial(com_name , com_speed) 
      

    def syncronize(self):
        n_sync_attempts = self.n_sync_attempts
        #sync phase
        while n_sync_attempts:
            for sync_byte in self.sync_seq:
                byte_read = self.port.read(1)[0]
                if byte_read != sync_byte:
                    n_sync_attempts -= 1
                    break
            else: return       
        if n_sync_attempts == 0:
            raise RuntimeError('fail to syncronize with arduino on port : ' + self.port.name)

    def getnext_sens_vals(self):
        sensors_data = []
        n_attempts = self.n_sync_attempts
        try:
            while n_attempts:
                self.syncronize()
                for i in range(self.n_sensors):
                    sensors_data.append(int.from_bytes(self.port.read(self.data_size),self.byteorder))
                '''
                for val in sensors_data:
                    if val < self.val_lim[0] or val >= self.val_lim[1]:
                        n_attempts -= 1
                        print('vibros')
                        sensors_data.clear()
                        break
                else: 
                    return sensors_data
            return None
            '''
                return sensors_data
        except OSError:
            return None

    def getnext_sens_tvals(self):
        sensors_data = []
        try:
            for i in range(self.n_sensors):
                read = self.port.readline() 
                print(read)
                print(str(read))
                split_str_data = str(self.port.readline()).split(';')
                split_str_data = [str_data.strip("b'\\nr") for str_data in split_str_data]
                sensors_data = [int(str_data) for str_data in split_str_data]
        except OSError:
            pass
        return sensors_data

    def perf_test(self,n_cycl_read):
        start = time.perf_counter()
        for i in range(n_cycl_read):
            self.getnext_sens_vals()
        return time.perf_counter() - start, n_cycl_read * self.n_sensors


class SensorPlot:

    def __init__(self,figure,**kwargs):
        self.figure = figure
        #for blitting
        self.background = None
        self.plot_number = kwargs.get('plot_number',1)
        #number of lines in the graph simultaniously
        self.vals_simult = kwargs.get('vals_simult',36)
        self.x = [mdates.date2num( dt.datetime.now()) for i in range(self.vals_simult)]
        self.y = [0 for i in range(self.vals_simult)]
        #self.x = [mdates.date2num( dt.datetime.now())]
        #self.y = [0]
        #axes params
        self.n_greed_lines = 16
        self.date_formatter = kwargs.get('date_formatter',mdates.DateFormatter('%M:%S:%f'))
        self.xdate_locator = kwargs.get('xdate_locator',mdates.ticker.LinearLocator(self.n_greed_lines))
        self.ydate_locator = kwargs.get('ydate_locator',mdates.ticker.LinearLocator(self.n_greed_lines))
        self.ylim = kwargs.get('ylim',(0,1024))
        self.fl_grid = kwargs.get('grid',True)
        self.nrows = kwargs.get('nrows',3)
        self.ncols = kwargs.get('ncols',1)
        self.title = kwargs.get('title','plot')
        self.xlabel = kwargs.get('xlabel','xlabel')
        self.ylabel = kwargs.get('ylabel','ylabel')
        self.axes = self.__get_axes()
        #lines params
        self.line_color = kwargs.get('line_color','red')
        self.line_width = kwargs.get('line_width',1.0)
        self.line_style = kwargs.get('line_style','-')
        self.marker = kwargs.get('marker','o')
        self.marker_facecolor = kwargs.get('marker_facecolor','red')
        self.marker_size = kwargs.get('marker_size',2.0);
        #initial graph - zero values
        self.__init_plot(False)

    def __get_axes(self):
        ax = self.figure.add_subplot(self.nrows,self.ncols,self.plot_number,axisbg='black')
        ax.set_title(self.title)
        ax.grid(self.fl_grid,color='w',linestyle='-',linewidth=0.3)
        ax.set_ylim(self.ylim)
        ax.xaxis.set_major_formatter(self.date_formatter)
        ax.xaxis.set_major_locator(self.xdate_locator)
        ax.yaxis.set_major_locator(self.ydate_locator)
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        return ax
    
    def plot(self):
        self.axes.plot(self.x,self.y,color=self.line_color,linewidth=self.line_width, linestyle=self.line_style, animated = True)
        ''' marker=self.marker,
                 markerfacecolor=self.marker_facecolor, markersize=self.marker_size, '''
    
    def plot_date(self):
        self.axes.plot_date(self.x,self.y)

    def __init_plot(self,blit=True):
        self.plot()
        plt.gcf().autofmt_xdate()
        if blit:
           self.background = self.figure.canvas.copy_from_bbox(self.axes.bbox)

    def update_plot_blit(self,y_val):
        self.x.append(mdates.date2num( dt.datetime.now()))
        self.y.append(y_val)
        self.y.pop(0)
        self.x.pop(0)
        self.figure.canvas.restore_region(self.background)
        self.axes.lines[0].set_xdata(self.x)
        self.axes.lines[0].set_ydata(self.y)
        self.axes.draw_artist(self.axes.lines[0])
        self.figure.canvas.blit(self.axes.bbox)

    def update_plot(self,y_val):
        self.x.append(mdates.date2num( dt.datetime.now()))
        self.y.append(y_val)
        self.y.pop(0)
        self.x.pop(0)
        del self.axes.lines[0]
        self.axes.set_xlim(self.x[0],self.x[len(self.x)- 1])
        self.plot()
        
    def update_line(self,y_val):
        self.x.append(mdates.date2num( dt.datetime.now()))
        self.y.append(y_val)
        self.y.pop(0)
        self.x.pop(0)
        self.axes.lines[0].set_data(self.x,self.y)
        self.axes.set_xlim(self.x[0],self.x[len(self.x)- 1])
        #helps redraw x label evil
        #self.axes.figure.canvas.draw()
        return self.axes.lines[0]


def animate(data,sensors_plots,com_mediator):
    data = com_mediator.getnext_sens_vals()
    data_it = iter(data)
    #print(data)
    #data = com_mediator.getnext_sens_vals()
    #print(data)
    lines = [sens_plt.update_line(next(data_it)) for sens_plt in sensors_plots]
    #lines = [sensors_plots[0].update_line(data[0]),sensors_plots[1].update_line(data[1]),sensors_plots[2].update_line(data[2])]
    #li = lines + sensors_plots[len(sensors_plots)-1].axes.get_xticklabels()
    return lines

if __name__ == '__main__':
    try:
        com_mediator = ComMediator('COM3',19200,n_sensors=3,data_size=2,byteorder='little',val_lim=(0,n_sampling_levels),n_sync_attempts=36)
    except serial.SerialException as e:
        print(e)
        sys.exit()
    #plt.ion() if  FuncAnimation -> then of it
    fig = plt.figure()
    fig.subplots_adjust(wspace=0.25,right=0.97)
    values_shown_simult = 64
    skin_resist_plot = SensorPlot(fig,plot_number=1,nrows=1,ncols=3,ylim=(0,n_sampling_levels),
                                  title='skin resistance monitor',xlabel='time', ylabel='skin resistance',vals_simult=values_shown_simult)
    heart_rate_plot = SensorPlot(fig,plot_number=2,nrows=1,ncols=3,ylim=(0,n_sampling_levels),
                                  title='heart rate monitor',xlabel='time', ylabel='heart rate',vals_simult=values_shown_simult)
    breathing_depth_plot = SensorPlot(fig,plot_number=3,nrows=1,ncols=3,ylim=(0,n_sampling_levels),
                                      title='breathing depth monitor',xlabel='time', ylabel='breathing depth',vals_simult=values_shown_simult)
    sensors_plots = [skin_resist_plot,heart_rate_plot,breathing_depth_plot]
    #fig.canvas.draw()
    #while True:
    #    sensors_data_it = iter(com_mediator.getnext_sens_vals())
    #    for sensor_plot in sensors_plots:
    #         sensor_plot.update_plot(next(sensors_data_it))   
    #    plt.pause(0.00001)
    #    plt.draw()
    ani = animation.FuncAnimation(fig,animate,fargs=(sensors_plots,com_mediator),interval=0,blit=True,repeat=True)
    plt.show()
       



    

        
         
    