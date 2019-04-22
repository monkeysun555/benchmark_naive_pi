import os
import logging
import numpy as np
import live_player
import live_server
import load
import math 

MS_IN_S = 1000.0
KB_IN_MB = 1000.0   # in ms

SEG_DURATION = 1000.0
CHUNK_DURATION = 200.0
CHUNK_SEG_RATIO = CHUNK_DURATION/SEG_DURATION
CHUNK_IN_SEG = SEG_DURATION/CHUNK_DURATION
BITRATE = [300.0, 500.0, 1000.0, 2000.0, 3000.0, 6000.0]

RANDOM_SEED = 11

DEFAULT_P = 0.8
DEFAULT_DELTA = SEG_DURATION / MS_IN_S
DEFAULT_RATE = 0

M_HIS_LEN = 3

FIRST_RATIO = 0.2
FIRST_THRES = 1
SECOND_RATIO = 0.1
SECOND_THRES = 2
THIRD_THRES = 3
INIT_M = 4

LOWEST_BUFF_THRES = 0.5

MIDIUM_BUFF_THRES = 0.75

class controller(object):
	"""docstring for Controller"""
	def __init__(self, target_buffer):
		# super(Controller, self).__init__()
		self.target_buffer = target_buffer
		self.last_buffer = 0.0
		self.p = DEFAULT_P
		self.last_rate = DEFAULT_RATE
		self.counter = 0
		# self.m = 0
		self.m_history = [INIT_M]*M_HIS_LEN

	def ReLU(self):
		return x * (x > 0)

	def cal_F(self, curr_buffer):
		buffer_diff = (curr_buffer - self.target_buffer) / MS_IN_S
		buffer_last_diff = (curr_buffer - self.last_buffer) / MS_IN_S
		f_q = 2 * math.exp(self.p * buffer_diff) / (1 + math.exp(self.p*buffer_diff))
		f_t = DEFAULT_DELTA / (DEFAULT_DELTA - buffer_last_diff)
		f_v = 1.0
		return f_q * f_t * f_v

	def quantize(self, quan_bw):
		for i in reversed(range(len(BITRATE))):
			if BITRATE[i] <= quan_bw:
				return i
		return 0

	def update_m(self, curr_buffer):
		temp_m = 0
		buffer_last_diff = (curr_buffer - self.last_buffer) / SEG_DURATION
		if buffer_last_diff >= FIRST_RATIO * DEFAULT_DELTA:
			temp_m = FIRST_THRES
		elif buffer_last_diff >= SECOND_RATIO * DEFAULT_DELTA:
			temp_m = SECOND_THRES
		else:
			temp_m = THIRD_THRES
		
		self.m_history = np.roll(self.m_history, -1)
		self.m_history[-1] = temp_m
		return np.mean(self.m_history)

	def update_target(self, freezing):
		self.target_buffer += freezing

	def choose_rate(self, est_bw, real_last_bw, curr_buffer, freezing):
		tuned_buffer = np.maximum(curr_buffer - freezing, 0.0)
		# print "Tuned buffer: ", tuned_buffer
		if tuned_buffer < self.target_buffer * LOWEST_BUFF_THRES:
			
			# # While buffer length is less than the lowest threshold
			# # Previously, we chosse bitrate fitting throughput
			# temp_rate = self.quantize(real_last_bw)
			# if temp_rate > self.last_rate + 1:
			# 	self.last_rate += 1
			# else:
			# 	self.last_rate = temp_rate

			# Another conservative	
			self.last_rate = 0

			self.last_buffer = curr_buffer
			if freezing > 0.0:
				self.update_target(freezing)
			return self.last_rate

		elif tuned_buffer < self.target_buffer * MIDIUM_BUFF_THRES:
			temp_rate = self.quantize(real_last_bw)
			if temp_rate > self.last_rate + 1:
				self.last_rate += 1
			else:
				self.last_rate = temp_rate
			self.last_buffer = curr_buffer
			if freezing > 0.0:
				self.update_target(freezing)
			return self.last_rate

		f = self.cal_F(tuned_buffer)	# Use curr_buffer or tuned_buff 
		# print "F value is: ", f
		tuned_bw = est_bw * f
		# print "Tunned bw: ", tuned_bw
		updated_m = self.update_m(tuned_buffer)
		# print(f, tuned_bw, updated_m)
		if tuned_bw > BITRATE[self.last_rate]:
			self.counter += 1
			if self.counter > updated_m:
				self.counter = 0
				temp_rate = self.quantize(est_bw)
				self.last_rate = temp_rate
				self.last_buffer = curr_buffer
				return temp_rate
		else:
			self.counter = 0
		self.last_buffer = curr_buffer

		return self.last_rate

	def test_reset(self, target_buffer):
		self.last_buffer = 0.0
		self.last_rate = DEFAULT_RATE
		self.counter = 0
		self.target_buffer = target_buffer
		self.m_history = [INIT_M]*M_HIS_LEN


	def main():
		pass

if __name__ == '__main__':
	main()
