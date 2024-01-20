# -*- coding: utf-8 -*-
"""
Created on Fri May 20 22:38:14 2022

@author: ScottStation
"""
import numpy as np
import pandas as pd

import scipy.stats as si
#from scipy.stats import norm
#N = norm.cdf

def get_d(S, K, T, r, vol):
    d1 = (np.log(S / K) + (r + 0.5 * vol ** 2) * T) / (vol * np.sqrt(T))
    d2 = d1 - vol * np.sqrt(T)
    return (d1,d2)   


def bs_call(S, K, T, r, vol):
    (d1,d2) = get_d(S, K ,T, r, vol)
    return S * si.norm.cdf(d1) - np.exp(-r * T) * K * si.norm.cdf(d2)

def bs_put(S, K, T, r, vol):
    (d1,d2) = get_d(S, K ,T, r, vol)
    return np.exp(-r * T) * K * si.norm.cdf(-d2) - S * si.norm.cdf(-d1)

def bs_vega(S, K, T, r, vol):
	d1 = get_d(S,K,T,r,vol)[0]
	return S * si.norm.pdf(d1) * np.sqrt(T) 

def bs_delta(S, K, T, r, vol, isCall):
	d1 = get_d(S,K,T,r,vol)[0]
	n = 1 if isCall else -1
	return  n * si.norm.cdf(n * d1)
	
def bs_gamma(S, K, T, r, vol):
	d1 = get_d(S,K,T,r,vol)[0]
	return  si.norm.pdf(d1) / (S * vol * np.sqrt(T))
  

def bs_theta(S, K, T, r, vol, isCall):
	(d1,d2) = get_d(S,K,T,r,vol)
	n = 1 if isCall else -1
	return  (-1 * (S * si.norm.pdf(d1) * vol) / (2 * np.sqrt(T)) - n * r * K * np.exp(-r * T) * si.norm.cdf(n * d2)) / 365
    


def find_vol(target_value, S, K, T, r, isCall=True):
    MAX_ITERATIONS = 200
    PRECISION = 1.0e-5
    MIN_VOL = 0.0002 # minimum volatility set to 0.02%
    sigma = 0.3
    for i in range(0, MAX_ITERATIONS):
        price = bs_call(S, K, T, r, sigma) if isCall else bs_put(S,K,T,r,sigma)
        vega = bs_vega(S, K, T, r, sigma)
        diff = target_value - price  # our root
        if (abs(diff) < PRECISION):
            return sigma
        sigma = max(sigma + diff/vega, MIN_VOL) # f(x) / f'(x), ensuring sigma is above minimum
    return sigma # value wasn't found, return best guess so far    