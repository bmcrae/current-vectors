import sys, time, string, os, math, re
import traceback
from sys import path
from string import split
from current_vectors import *

logFilePath = None
arrowOptions = {} 

try:
    ####### USER SETTINGS ##############################
    if len(sys.argv) < 2: #Manual inputs
        arrowOptions['configFile'] = 'C:\\temp\\pinchpoint_config3.ini'
        arrowOptions['voltMapFile'] = 'C:\\temp\\rastert_li_med_1.asc'       
        arrowOptions['outDir'] = 'c:\\temp\\out'
        arrowOptions['writeTotalCurrent'] = True # Write total current leaving each pixel
        arrowOptions['writeResultant'] = True # Write vector magnitudes (will be less than total current)
        arrowOptions['writeAllDirections'] = True # Write current leaving pixels from N, NE, E, etc..
        arrowOptions['writeArcVectors'] = True # Create an ESRI shapefile with angle and magnitude information
        arrowOptions['deleteTempFiles'] = True # Delete everything except standard current map (saved for debug)
    ####################################################
        
    else:
        arrowOptions['configFile'] = sys.argv[1]
        arrowOptions['voltMapFile'] = sys.argv[2]
        arrowOptions['outDir'] = sys.argv[3]
        arrowOptions['writeTotalCurrent']  = sys.argv[4]
        arrowOptions['writeResultant']  = sys.argv[5]
        arrowOptions['writeAllDirections']  = sys.argv[6]
        arrowOptions['writeArcVectors']  = sys.argv[7]
        arrowOptions['deleteTempFiles']  = sys.argv[8]        
    
    # Map vectors
    map_current_vectors(arrowOptions) 

except:
    exit_with_python_error(logFilePath,'run_current_vectors.py')
        
        