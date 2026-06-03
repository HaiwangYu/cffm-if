#!/usr/bin/env python

import sys
import numpy as np
import h5py
import matplotlib.pyplot as plt


if __name__ == '__main__':

  fn = sys.argv[1]
  key = sys.argv[2]
  iapa = int(sys.argv[3])
  print(f"File: {fn}, Key: {key}, APA: {iapa}")
  

  data = h5py.File(fn, 'r')
  f = data.get(key)
  if f is None:
    print('f is None')
    print('Available keys:')
    for k in data.keys():
      print(k)
    exit()
  frame = np.array(f)
  print(frame.shape)
  frame = frame[2560*(iapa):2560*(iapa+1),:]
  print(frame.shape)
  frame=np.transpose(frame)
  frame_ma = np.ma.array(frame)

  plt.gca().set_title(key)
  # plt.imshow(np.ma.masked_where(frame_ma<=0,frame_ma), cmap="rainbow", interpolation="none"
  # plt.imshow(frame_ma>0, cmap="viridis", interpolation="none"
  plt.imshow(frame_ma, cmap="rainbow", interpolation="none"
  # , extent = [0 , 2560, 0 , 6000]
  , origin='lower'
  , aspect='auto'
  # , aspect=0.8/4.7
  # , aspect=0.1
  )
  plt.clim([-100,100])

  plt.grid() 
  plt.show()



