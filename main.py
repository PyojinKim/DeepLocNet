# basic includes
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from random import random, randint
from numpy.random import randint as ri
from pdb import set_trace as bp
import scipy.io as sio

# include pylayers map creator
from include.createMap import createMap
# include RRT Planner
from include.rrtPlanner import calculatePath
# include distance calculator
from include.calculateDists import calculateDist
# include PF/Fast SLAM v1
from include.localize import localize

# include real WiFi Scanner (optional)
# from include.wifiScanner import *
# from include.scannerUbuntu import *

##############################################################
# Parse Arguments
##############################################################
parser = argparse.ArgumentParser(description='Radio-Inertial Localization')
parser.add_argument('--map', type=int, default=1, metavar='input blueprint (default: 1), range 1-15')
parser.add_argument('--dim', type=int, default=2, metavar='dimension for localization (default: 2)')
parser.add_argument('--z', type=int, default=2, metavar='maximum height of workspace (default: 2)')
parser.add_argument('--np', type=int, default=3000, metavar='number of particles for localization (default: 3000)')
parser.add_argument('--iter', type=int, default=4, metavar='number of iterations for RRT (default: 4 (implies 10^4))')
parser.add_argument('--step', type=float, default=3, metavar='step size for RRT (default: 3)')
parser.add_argument('--su', type=float, default=0.8, metavar='action model noise (default: 0.8)')
parser.add_argument('--R', type=int, default=10, metavar='sensing range of robot (default: 10)')
parser.add_argument('--slam', type=int, default=0, metavar='use Fast SLAM(FS) or Particle Filter(PF) (default: 0 (PF))')
parser.add_argument('--useClas', type=int, default=0, metavar='use classifier or not (default: 0)')
parser.add_argument('--hard', type=int, default=0, metavar='use hard or soft classification (default: 0 (soft))')
parser.add_argument('--savemat', type=int, default=0, metavar='save mat file for plotting or not (default : 0 (no))')

args = parser.parse_args()

##############################################################
# Global Parameters
##############################################################
# custom *.INI files
inis        = ["defstr.ini", "office.ini", "11Dbibli.ini", "DLR.ini", "DLR2.ini", "Luebbers.ini", "TC2_METIS.ini", "TC1_METIS.ini", "W2PTIN.ini", "defdiff.ini", "defsthdiff.ini", "edge.ini", "homeK_vf.ini", "klepal.ini", "testair0.ini"] 
# start configurations corresponding to *.INI file
starts      = [[20,20,0.2], [20,80,0.4], [5,5,0.8], [20,15,1.0], [20,15,1.2], [2,2,1.4], [80,50,1.8], [15,25,2.0], [80,20,1.7], [10,10,1.5], [5,5,1.1], [10,10,0.7], [35,10,0.5], [5,40,0.3], [10,10,0.1]]
# goal configurations corresponding to *.INI file
goals       = [[60,110,0.1], [18,15,0.3], [10,135,0.7], [20,55,0.5], [20,55,1.5], [50,50,1.3], [5,65,1.6], [65,125,1.8], [30,75,1.2], [24,53,1.4], [5,60,0.6], [50,60,0.4], [25,45,0.2], [20,80,1.8], [28,52,0.8]]
# which map to select
mapID       = args.map - 1

##############################################################
# Pylayers map
##############################################################
# Parameters for RSSI Generation
dim         = args.dim                                      # dimension of localization 2, 3(works only with pylayers)
layout      = inis[mapID]                                   # blueprint for pylayers map generation. Set to "" for random map
maxZ        = args.z                                        # maxHeight
su          = args.su                                       # motion model noise

mat = createMap(layout, dim, maxZ)
if dim == 2 : mat.cover()
if dim == 3 : mat.cover3D()

##############################################################
# Run RRT on Map
##############################################################
# Parameters for random walk
start = starts[mapID]                                       # start position for random walk (chosen at random)
goal  = goals[mapID]                                        # goal position for random walk (chosen at random)
step  = args.step                                           # step size of random walk

RRT = calculatePath(start, goal, mat, step, dim, 10**args.iter)
wayPts = RRT.RRTSearch()

if(len(wayPts)==1): print("No waypoints found! Try using a smaller step size using --step flag"); sys.exit()

##############################################################
# Calculate RSSI and Actual Distances
##############################################################
distMap = calculateDist(wayPts, mat, dim)
if dim == 2: dists = distMap.readDistances()
if dim == 3: dists = distMap.readDistances3D()

##############################################################
# Run Particle Filter / Fast SLAM v1 depending on choice
##############################################################
# Parameters for localization
numP        = args.np                                       # number of particles used
sigU        = [random()*su, random()*su, random()*0.5*su]   # motion model noise - typically a fraction of the step size
sigZ        = ri(10,100, size=mat.numAPs)                   # measure model noise
senseR      = args.R                                        # sensing range
useClas     = args.useClas                                  # use of classifier or not
hardClas    = args.hard                                     # use soft vs hard classification
slam        = args.slam                                     # use fast slam or particle filter
viz3D       = False                                         # visualize only 3D in both 2D/3D localization cases

# Run the localization algorithms
localizer = localize(numP, sigU, sigZ, dists, mat, wayPts, senseR, dim, useClas, hardClas)

if slam==1:
    localizer.FastSLAM()
    print("The MSE in the localized path is:", localizer.MSE())
    print("The point-wise error in localization is: ",localizer.getCDF())
    print("The LOS/NLOS counts are: ", distMap.printLNL())
    if useClas: print("The confidence values are [TP, FP, TN, FN]: ",localizer.confidence)

    if viz3D: 
        mat.visualize3D(start, goal, wayPts, localizer.path, localizer.APLocs, localizer.IDs)
    else:
        if dim == 2: mat.visualize(start, goal, wayPts, localizer.path, localizer.APLocs, localizer.IDs)
        if dim == 3: mat.visualize3D(start, goal, wayPts, localizer.path, localizer.APLocs, localizer.IDs)
else:
    localizer.particleFilter()
    print("The MSE in the localized path is:", localizer.MSE())
    print("The point-wise error in localization is: ",localizer.getCDF())
    print("The LOS/NLOS counts are: ", distMap.printLNL())
    if useClas: print("The confidence values are [TP, FP, TN, FN]: ",localizer.confidence)

    if viz3D: 
        mat.visualize3D(start, goal, wayPts, localizer.path)
    else:
        if dim == 2: mat.visualize(start, goal, wayPts, localizer.path)
        if dim == 3: mat.visualize3D(start, goal, wayPts, localizer.path)
    
if args.savemat:
    dic = {}
    dic['dim'] = dim
    dic['start'] = start
    dic['goal'] = goal
    dic['slam'] = slam
    dic['mse'] = localizer.MSE()
    dic['cdf'] = localizer.getCDF()
    dic['confidence'] = localizer.confidence
    dic['lnl'] = distMap.LNL
    dic['waypts'] = wayPts
    dic['path'] = localizer.path
    dic['sigu'] = sigU
    dic['sigz'] = sigZ
    dic['R'] = senseR
    dic['Tx'] = mat.Tx
    dic['map'] = mat.map
    if slam==0: dic['TX'] = mat.Tx
    if slam==1: dic['TX'] = localizer.APLocs
    if slam==1: dic['TX_ids'] = localizer.IDs
    sio.savemat('trial.mat', dic)